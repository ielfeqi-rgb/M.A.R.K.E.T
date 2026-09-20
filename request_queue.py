"""
M.A.R.K.E.T AI - Smart Asynchronous Request Queue & Virtual Workspace Concurrency Scheduler
Serializes per-session turns, prevents cross-context contamination, and schedules AI workers fairly.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, Awaitable
from request_validator import StandardAIRequest, ValidationResult, validate_and_guard_request

logger = logging.getLogger(__name__)


@dataclass(order=True)
class QueuedRequestItem:
    priority_score: int
    timestamp: float
    request: StandardAIRequest = field(compare=False)
    future: asyncio.Future = field(compare=False)
    created_at: float = field(default_factory=time.time, compare=False)


class SmartAIRequestQueue:
    """
    Enterprise Asynchronous AI Request Queue with Per-Session Serialization
    and Virtual Workspace Isolation.
    """
    _instance = None

    def __init__(self, max_workers: int = 4, max_queue_size: int = 5000):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self._queue: asyncio.PriorityQueue[QueuedRequestItem] = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._processor_func: Optional[Callable[[StandardAIRequest], Awaitable[Dict[str, Any]]]] = None

        # Telemetry Metrics
        self.total_enqueued = 0
        self.total_processed = 0
        self.total_rejected = 0
        self.total_latency_ms = 0
        self.last_latencies = []

    @classmethod
    def get_instance(cls, max_workers: int = 4):
        if not cls._instance:
            cls._instance = SmartAIRequestQueue(max_workers=max_workers)
        return cls._instance

    def set_processor(self, func: Callable[[StandardAIRequest], Awaitable[Dict[str, Any]]]):
        """Set the core execution engine that processes grounded AI turns."""
        self._processor_func = func

    def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self._session_locks:
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_locks[session_id]

    async def start(self):
        """Start async worker tasks."""
        if self._running:
            return
        self._running = True
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
        logger.info(f"Smart AI Request Queue online with {self.max_workers} concurrent workers.")

    async def stop(self):
        """Cleanly cancel all workers on shutdown."""
        self._running = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("Smart AI Request Queue workers shut down cleanly.")

    async def enqueue(self, raw_req_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Public entrypoint:
        1. Validates and guards against malformed/noise requests.
        2. If invalid, rejects immediately or returns fast greeting fallback.
        3. If valid, serializes into queue and awaits fulfillment.
        """
        t_start = time.time()
        try:
            req = StandardAIRequest(**raw_req_dict)
        except Exception as e:
            self.total_rejected += 1
            return {
                "status": "rejected",
                "rejection_code": "INVALID_SCHEMA",
                "error": f"صيغة الطلب غير مطابقة للمواصفات: {str(e)}",
                "reply": "عذراً، تعذر قراءة رسالتك. يرجى كتابة نص واضح للمنتج أو المقاس.",
                "latency_ms": int((time.time() - t_start) * 1000)
            }

        # Pre-AI Gatekeeper validation
        val_result: ValidationResult = validate_and_guard_request(req)
        if not val_result.is_valid:
            self.total_rejected += 1
            logger.info(f"Request filtered by Pre-AI Guard [{val_result.rejection_code}]: '{req.message[:40]}'")
            return {
                "status": "filtered",
                "rejection_code": val_result.rejection_code,
                "rejection_reason": val_result.rejection_reason,
                "reply": val_result.fast_fallback_reply or "تفضل يا فندم بسؤالك وسنساعدك فوراً. ✨",
                "filtered_pre_ai": True,
                "latency_ms": int((time.time() - t_start) * 1000)
            }

        # Fast Greeting Short-Circuit (Zero LLM cost & 0ms latency)
        if val_result.category == "greeting" and val_result.fast_fallback_reply:
            self.total_processed += 1
            return {
                "status": "success",
                "reply": val_result.fast_fallback_reply,
                "is_fast_greeting": True,
                "latency_ms": int((time.time() - t_start) * 1000)
            }

        # Push to Queue with Priority (Higher priority number gets processed first)
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        # In PriorityQueue, lower score = higher priority
        priority_score = 100 - (req.priority * 10)

        item = QueuedRequestItem(
            priority_score=priority_score,
            timestamp=t_start,
            request=req,
            future=future
        )

        try:
            self._queue.put_nowait(item)
            self.total_enqueued += 1
        except asyncio.QueueFull:
            self.total_rejected += 1
            return {
                "status": "error",
                "error": "طابور المعالجة ممتلئ حالياً بسبب ضغط الطلبات، يرجى المحاولة بعد لحظات.",
                "reply": "الخادم يشهد ضغطاً بسيطاً حالياً، جاري معالجة طلبك قريباً. ⏳",
                "latency_ms": int((time.time() - t_start) * 1000)
            }

        # Wait for worker to fulfill future
        try:
            result = await asyncio.wait_for(future, timeout=45.0)
            elapsed_ms = int((time.time() - t_start) * 1000)
            self.total_processed += 1
            self.total_latency_ms += elapsed_ms
            self.last_latencies.append(elapsed_ms)
            if len(self.last_latencies) > 20:
                self.last_latencies.pop(0)
            result["queue_latency_ms"] = elapsed_ms
            return result
        except asyncio.TimeoutError:
            self.total_rejected += 1
            return {
                "status": "error",
                "error": "Request timed out in queue",
                "reply": "عذراً، استغرقت المعالجة وقتاً أطول من المعتاد، يرجى إعادة المحاولة.",
                "latency_ms": int((time.time() - t_start) * 1000)
            }

    async def _worker_loop(self, worker_id: int):
        """Worker loop continuously popping queued requests and executing them."""
        while self._running:
            try:
                item: QueuedRequestItem = await self._queue.get()
                req = item.request

                # Enforce per-session serialization so turn order is preserved strictly
                session_lock = self._get_session_lock(req.session_id)
                async with session_lock:
                    try:
                        if self._processor_func:
                            res = await self._processor_func(req)
                        else:
                            res = {
                                "status": "success",
                                "reply": f"تم استلام رسالتك في مساحة العمل ({req.workspace_id}): {req.message}",
                                "executed_steps": [1, 2, 4]
                            }

                        if not item.future.done():
                            item.future.set_result(res)
                    except Exception as ex:
                        logger.error(f"Worker {worker_id} error processing request: {ex}")
                        if not item.future.done():
                            item.future.set_result({
                                "status": "error",
                                "error": str(ex),
                                "reply": "حدث خطأ أثناء معالجة الرد، يرجى المحاولة مرة أخرى."
                            })
                    finally:
                        self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} exception in loop: {e}")
                await asyncio.sleep(0.1)

    def get_stats(self) -> Dict[str, Any]:
        """Return live telemetry metrics for the dashboard."""
        avg_latency = (
            int(sum(self.last_latencies) / len(self.last_latencies))
            if self.last_latencies else 0
        )
        return {
            "status": "online" if self._running else "idle",
            "active_workers": len(self._workers),
            "pending_in_queue": self._queue.qsize(),
            "total_enqueued": self.total_enqueued,
            "total_processed": self.total_processed,
            "total_rejected_or_filtered": self.total_rejected,
            "avg_latency_ms": avg_latency,
            "active_session_locks": len(self._session_locks)
        }


# Global singleton queue instance
ai_queue = SmartAIRequestQueue.get_instance()
