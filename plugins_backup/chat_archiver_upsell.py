"""
M.A.R.K.E.T Plugin: Chat Archiver & Mock Upsell Trigger
- Archives all completed purchase conversations to a local log/JSON file.
- Triggers custom mock promotional/upsell offers when a purchase intent is detected.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from plugin_manager import BasePlugin

logger = logging.getLogger(__name__)


class Plugin(BasePlugin):
    plugin_id = "chat_archiver_upsell"
    name = "أرشفة المحادثات والعروض المخصصة"
    description = "تقوم بأرشفة محادثات الشراء الناجحة وتوليد عروض وهمية/مخصصة للعملاء بعد إتمام الشراء."
    version = "1.0.0"
    author = "Local AI Generator"
    enabled = True

    def __init__(self):
        self.archive_dir = os.path.expanduser("~/omnicontext_ai/archives")
        os.makedirs(self.archive_dir, exist_ok=True)

    def on_reply_generated(self, user_id: str, prompt: str, reply: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Inspect if the conversation involved buying or purchasing."""
        t = (prompt + " " + reply).lower()
        purchase_keywords = ["شراء", "اشتري", "طلب", "حجز", "سعر", "ج.م", "جنيه", "اريد"]
        
        is_purchase = any(kw in t for kw in purchase_keywords)
        if is_purchase:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            archive_entry = {
                "timestamp": timestamp,
                "user_id": user_id,
                "user_prompt": prompt,
                "ai_reply": reply,
                "metadata": metadata
            }
            
            archive_file = os.path.join(self.archive_dir, "purchase_conversations.json")
            try:
                records = []
                if os.path.exists(archive_file):
                    with open(archive_file, "r", encoding="utf-8") as f:
                        records = json.load(f)
                records.append(archive_entry)
                with open(archive_file, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                
                logger.info(f"[Plugin/Archiver] Archived purchase conversation for user {user_id} to {archive_file}")
            except Exception as e:
                logger.error(f"[Plugin/Archiver Error] Failed to archive: {e}")

            # Generate mock upsell offer
            mock_offer = "🎁 **عرض خاص من المتجر!** احصل على خصم 15% إضافي على طلبك القادم باستخدام الكود: `SPECIAL15`."
            return {
                "archived": True,
                "mock_upsell_offer": mock_offer
            }

        return None
