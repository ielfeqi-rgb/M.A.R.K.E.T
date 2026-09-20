"""
M.A.R.K.E.T AI - Authentication, RBAC, and Session Security Engine
"""

import os
import hmac
import hashlib
import secrets
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import Header, HTTPException, Depends

logger = logging.getLogger(__name__)

# Default standard role permissions mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "admin": [
        "products_view",
        "products_edit",
        "orders_manage",
        "studio_edit",
        "whatsapp_chat",
        "debugger_view",
        "settings_manage",
        "users_manage",
        "reports_view",
        "cs_pool_manage",
    ],
    "cs": [
        "cs_pool_manage",
        "whatsapp_chat",
        "products_view",
        "orders_manage",
        "debugger_view",
    ],
    "it": [
        "products_view",
        "studio_edit",
        "debugger_view",
        "settings_manage",
        "reports_view",
    ],
    "sales": [
        "products_view",
        "products_edit",
        "orders_manage",
        "whatsapp_chat",
        "debugger_view",
    ],
    "worker": [
        "products_view",
        "orders_manage",
        "whatsapp_chat",
    ],
}

ALL_PERMISSIONS = [
    {"id": "cs_pool_manage", "label": "إدارة واستلام تحويلات خدمة العملاء (Support Center)", "category": "خدمة العملاء"},
    {"id": "products_view", "label": "عرض بيانات المخزون والمنتجات المعتمدة", "category": "المخزون والمبيعات"},
    {"id": "products_edit", "label": "تعديل الأسعار والمخزون وإجراء المزامنة", "category": "المخزون والمبيعات"},
    {"id": "orders_manage", "label": "إجراء ومتابعة أوامر الشراء والطلبات", "category": "المخزون والمبيعات"},
    {"id": "whatsapp_chat", "label": "الوصول لبوابة المحادثات والتواصل المباشر", "category": "المراسلات"},
    {"id": "debugger_view", "label": "منصة الفحص والتدقيق التشغيلي", "category": "المراسلات"},
    {"id": "studio_edit", "label": "استوديو المسارات وبناء العقد البرمجية", "category": "المسارات والتكامل"},
    {"id": "settings_manage", "label": "تعديل إعدادات المنظومة ومحركات المعالجة", "category": "النظم والـ IT"},
    {"id": "users_manage", "label": "إدارة حسابات المستخدمين وتعيين الصلاحيات", "category": "الإدارة العامة"},
    {"id": "reports_view", "label": "عرض لوحة المؤشرات وقراءات النظام التشغيلية", "category": "الإدارة العامة"},
]


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${pw_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt$hash format."""
    try:
        if not stored_hash or '$' not in stored_hash:
            return False
        salt, expected_hash = stored_hash.split('$', 1)
        calculated_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return hmac.compare_digest(calculated_hash, expected_hash)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def generate_session_token() -> str:
    """Generate secure random 32-byte session token hex."""
    return secrets.token_hex(32)


def get_default_permissions_for_role(role: str) -> List[str]:
    """Get predefined permissions list for a standard role."""
    return ROLE_PERMISSIONS.get(role.lower(), ROLE_PERMISSIONS.get("sales", []))
