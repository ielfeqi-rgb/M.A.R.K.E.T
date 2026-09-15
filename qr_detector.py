import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List
from dataclasses import dataclass
from settings import settings

logger = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None

# Safe import for cv2 and numpy if available
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.info("OpenCV/NumPy not installed. Image QR detection will run in lightweight fallback mode.")


def get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="qr-detector")
    return _executor


@dataclass
class QRResult:
    data: str
    confidence: float
    region: str


def _detect_qr_sync(image_bytes: bytes) -> Optional[QRResult]:
    if not CV2_AVAILABLE:
        return None

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("Failed to decode image")
            return None

        max_dim = max(img.shape[:2])
        if max_dim > 1600:
            h_orig, w_orig = img.shape[:2]
            scale = 1600 / max_dim
            img = cv2.resize(img, (int(w_orig * scale), int(h_orig * scale)))

        h, w = img.shape[:2]
        detector = cv2.QRCodeDetector()

        # Regions check
        regions = [
            ("full", img),
            ("bottom_right", img[h//2:, w//2:]),
            ("bottom_left", img[h//2:, :w//2]),
            ("top_right", img[:h//2, w//2:]),
            ("top_left", img[:h//2, :w//2]),
            ("center", img[h//4:3*h//4, w//4:3*w//4]),
        ]

        for region_name, region_img in regions:
            data, _, _ = detector.detectAndDecode(region_img)
            if data and data.strip():
                logger.info(f"QR found in {region_name}: {data.strip()[:50]}...")
                return QRResult(data=data.strip(), confidence=0.9, region=region_name)

        # Grayscale check
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        data, _, _ = detector.detectAndDecode(gray)
        if data and data.strip():
            return QRResult(data=data.strip(), confidence=0.8, region="grayscale")

        return None
    except Exception as e:
        logger.error(f"QR detection error: {e}")
        return None


async def detect_qr_code(image_bytes: bytes) -> Optional[str]:
    if not CV2_AVAILABLE:
        return None

    if len(image_bytes) > settings.qr_max_image_size:
        logger.warning(f"Image too large: {len(image_bytes)} bytes")
        return None

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        get_executor(),
        _detect_qr_sync,
        image_bytes
    )
    return result.data if result else None


def shutdown_executor():
    global _executor
    if _executor:
        _executor.shutdown(wait=True)
        _executor = None