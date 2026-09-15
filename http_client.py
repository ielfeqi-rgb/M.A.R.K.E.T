import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from settings import settings

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    _instance: Optional["AsyncHTTPClient"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._ollama_client: Optional[httpx.AsyncClient] = None
        self._fb_client: Optional[httpx.AsyncClient] = None
        self._ngrok_client: Optional[httpx.AsyncClient] = None
        self._general_client: Optional[httpx.AsyncClient] = None

    @classmethod
    async def get_instance(cls) -> "AsyncHTTPClient":
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._init_clients()
        return cls._instance

    async def _init_clients(self):
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)

        self._ollama_client = httpx.AsyncClient(
            base_url=settings.ollama_url.rstrip("/"),
            timeout=httpx.Timeout(settings.ollama_timeout),
            limits=limits,
        )

        self._fb_client = httpx.AsyncClient(
            base_url=settings.fb_api_url,
            timeout=httpx.Timeout(settings.fb_api_timeout),
            limits=limits,
            headers={"Authorization": f"Bearer {settings.fb_page_token}"},
        )

        self._ngrok_client = httpx.AsyncClient(
            base_url="https://api.ngrok.com",
            timeout=httpx.Timeout(settings.ngrok_timeout),
            headers={
                "Authorization": f"Bearer {settings.ngrok_authtoken}",
                "Ngrok-Version": "2",
            } if settings.ngrok_authtoken else {},
        ) if settings.ngrok_authtoken else None

        self._general_client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
        )

        logger.info("HTTP clients initialized with connection pooling")

    async def close(self):
        for client in [self._ollama_client, self._fb_client, self._ngrok_client, self._general_client]:
            if client:
                await client.aclose()
        logger.info("HTTP clients closed")

    @property
    def ollama(self) -> httpx.AsyncClient:
        if not self._ollama_client:
            raise RuntimeError("Ollama client not initialized")
        return self._ollama_client

    @property
    def facebook(self) -> httpx.AsyncClient:
        if not self._fb_client:
            raise RuntimeError("Facebook client not initialized")
        return self._fb_client

    @property
    def ngrok(self) -> Optional[httpx.AsyncClient]:
        return self._ngrok_client

    @property
    def general(self) -> httpx.AsyncClient:
        if not self._general_client:
            raise RuntimeError("General client not initialized")
        return self._general_client


class RetryPolicy:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        retry_on_status: tuple = (429, 500, 502, 503, 504),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_status = retry_on_status

    async def execute(self, func, *args, **kwargs):
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await func(*args, **kwargs)
                if response.status_code in self.retry_on_status:
                    raise httpx.HTTPStatusError(
                        f"Status {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                return response
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.exponential_base ** attempt),
                        self.max_delay,
                    )
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed: {e}")

        raise last_exception


ollama_retry = RetryPolicy(max_retries=settings.ollama_max_retries)
fb_retry = RetryPolicy(max_retries=settings.fb_max_retries)
ngrok_retry = RetryPolicy(max_retries=2, base_delay=2.0)


async def close_all_clients():
    """Close all HTTP clients gracefully"""
    instance = AsyncHTTPClient._instance
    if instance:
        await instance.close()
        AsyncHTTPClient._instance = None