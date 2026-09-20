"""
M.A.R.K.E.T AI - Enterprise API Request Normalizer & Pre-AI Guard
Enforces structured schema, sanitizes input, and filters invalid/spam requests before touching LLMs.
"""

import re
import time
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Request deduplication and rate-limiting cache (session_id: last_request_timestamp)
_SESSION_RATE_CACHE: TTLCache = TTLCache(maxsize=10000, ttl=60)
_LAST_MESSAGE_HASH_CACHE: TTLCache = TTLCache(maxsize=10000, ttl=10)


class StandardAIRequest(BaseModel):
    """
    Standardized API Request Schema for all AI turns across channels & employee sessions.
    """
    message: str = Field(..., min_length=1, max_length=1500, description="Customer or employee prompt message")
    session_id: str = Field(default="session_default", min_length=1, max_length=120, description="Unique conversation session or customer phone")
    workspace_id: str = Field(default="ws_default", min_length=1, max_length=120, description="Virtual workspace / isolated employee context")
    employee_id: Optional[int] = Field(default=None, description="ID of the employee managing this session")
    employee_name: Optional[str] = Field(default=None, description="Name of the employee")
    channel: str = Field(default="simulator", description="whatsapp, messenger, telegram, simulator, or api")
    priority: int = Field(default=1, ge=1, le=5, description="1=Normal, 5=Urgent/VIP Handover")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom grounding or context metadata")

    @field_validator("message")
    @classmethod
    def sanitize_message_field(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("نص الرسالة فارغ أو يحتوي على مسافات فقط")
        # Strip invisible non-printable control characters
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', v.strip())
        if len(cleaned) > 1500:
            cleaned = cleaned[:1500]
        return cleaned


class ValidationResult(BaseModel):
    is_valid: bool
    sanitized_message: str
    rejection_code: Optional[str] = None
    rejection_reason: Optional[str] = None
    fast_fallback_reply: Optional[str] = None
    category: str = "normal"  # normal, greeting, spam, gibberish, empty


def validate_and_guard_request(req: StandardAIRequest) -> ValidationResult:
    """
    Pre-AI Gatekeeper:
    Inspects, sanitizes, and filters the request before putting it in the AI inference queue.
    """
    raw_msg = req.message.strip()

    # 1. Empty / Whitespace check
    if not raw_msg or len(raw_msg) == 0:
        return ValidationResult(
            is_valid=False,
            sanitized_message="",
            rejection_code="EMPTY_MESSAGE",
            rejection_reason="الرسالة فارغة تماماً",
            fast_fallback_reply="أهلاً بك يا فندم! كيف يمكننا مساعدتك اليوم؟ ✨",
            category="empty"
        )

    # 2. Pure punctuation or keyboard smash / repetitive characters check (e.g., ".......", "asdfghjk", "؟؟؟؟؟؟")
    if re.fullmatch(r'^[^\w\s\u0600-\u06FF]+$', raw_msg):
        return ValidationResult(
            is_valid=False,
            sanitized_message=raw_msg,
            rejection_code="PUNCTUATION_ONLY",
            rejection_reason="الرسالة تحتوي فقط على علامات ترقيم ورموز غير مفهومة",
            fast_fallback_reply="أهلاً بحضرتك يا فندم! تفضل بسؤالك أو استفسارك وسنساعدك فوراً. 😊",
            category="gibberish"
        )

    # Repetitive single character repetition like "ههههههههههههههههههههههههههههههههههههههههههههه" or "aaaaaaa"
    if len(raw_msg) > 8 and len(set(raw_msg)) <= 2:
        return ValidationResult(
            is_valid=False,
            sanitized_message=raw_msg,
            rejection_code="REPETITIVE_NOISE",
            rejection_reason="الرسالة تحتوي على تكرار نمطي لحرف واحد",
            fast_fallback_reply="أهلاً بحضرتك يا فندم، كيف نقدر نساعدك؟ ✨",
            category="gibberish"
        )

    # 3. Duplicate Message Flood Guard (Rapid identical message within 5 seconds)
    msg_hash = f"{req.session_id}:{raw_msg}"
    if msg_hash in _LAST_MESSAGE_HASH_CACHE:
        return ValidationResult(
            is_valid=False,
            sanitized_message=raw_msg,
            rejection_code="DUPLICATE_MESSAGE",
            rejection_reason="تم إرسال نفس الرسالة للتو، جاري معالجة الرد السابق",
            fast_fallback_reply="جاري معالجة طلبك السابق يا فندم، لحظة واحدة فضلاً. ⏳",
            category="spam"
        )
    _LAST_MESSAGE_HASH_CACHE[msg_hash] = time.time()

    # 4. Standard Greetings Fast-Path (Optionally handle common 1-word greetings directly)
    clean_lower = raw_msg.lower()
    common_greetings = ["السلام عليكم", "سلام عليكم", "مرحبا", "مساء الخير", "صباح الخير", "هاي", "hello", "hi"]
    if clean_lower in common_greetings or raw_msg in ["سلام", "أهلاً"]:
        return ValidationResult(
            is_valid=True,
            sanitized_message=raw_msg,
            fast_fallback_reply="وعليكم السلام ورحمة الله وبركاته يا فندم! أهلاً بيك في M.A.R.K.E.T. نورتنا، تحب تستفسر عن منتج معين أو مقاسات متاحة؟ ✨",
            category="greeting"
        )

    # Validated and passed all gatekeeper checks
    return ValidationResult(
        is_valid=True,
        sanitized_message=raw_msg,
        category="normal"
    )
