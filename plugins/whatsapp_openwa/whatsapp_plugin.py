"""
WhatsApp OpenWA — M.A.R.K.E.T BasePlugin Integration
=====================================================
This plugin hooks into the M.A.R.K.E.T plugin system to:
1. Tag incoming WhatsApp messages for special handling
2. Auto-send AI replies back via WhatsApp
3. Send purchase confirmation messages via WhatsApp
4. Display WhatsApp connection status badge in dashboard
"""

import logging
from typing import Dict, Any, Optional

from plugin_manager import BasePlugin

logger = logging.getLogger(__name__)


class Plugin(BasePlugin):
    plugin_id = "whatsapp_openwa"
    name = "واتساب (OpenWA Gateway)"
    description = (
        "تكامل واتساب كامل عبر بوابة OpenWA مفتوحة المصدر. "
        "يدعم إرسال واستقبال الرسائل، مسح QR Code، "
        "والرد التلقائي بالذكاء الاصطناعي على محادثات الواتساب."
    )
    version = "1.0.0"
    author = "M.A.R.K.E.T AI Systems"
    enabled = True

    def __init__(self):
        self._wa_adapter = None

    def _get_adapter(self):
        """Lazy-load the WhatsApp adapter to avoid circular imports."""
        if self._wa_adapter is None:
            try:
                from plugins.whatsapp_openwa.adapter import WhatsAppAdapter
                import json
                import os

                config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
                config = {}
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)

                self._wa_adapter = WhatsAppAdapter(
                    openwa_url=config.get("whatsapp_openwa_url", "http://localhost:2785"),
                    api_key=config.get("whatsapp_openwa_api_key", ""),
                    session_id=config.get("whatsapp_session_id", "market-bot"),
                )
            except Exception as e:
                logger.error(f"[WhatsApp Plugin] Failed to initialize adapter: {e}")
        return self._wa_adapter

    def on_message_received(self, user_id: str, message: str) -> Optional[Dict[str, Any]]:
        """
        Hook: Triggered when any message is received.
        Tags WhatsApp messages for the AI pipeline.
        """
        # Check if user_id looks like a WhatsApp chat ID
        if user_id and ("@c.us" in user_id or "@g.us" in user_id):
            logger.info(f"[WhatsApp Plugin] WhatsApp message from {user_id}: {message[:50]}...")
            return {
                "source": "whatsapp",
                "platform": "whatsapp",
                "chat_id": user_id,
                "requires_wa_reply": True,
                "message": message,
            }
        return None

    def on_reply_generated(
        self, user_id: str, prompt: str, reply: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Hook: Triggered after AI generates a reply.
        If the original message was from WhatsApp, send the reply back via WhatsApp.
        """
        meta = metadata or {}
        if meta.get("source") == "whatsapp" or (
            user_id and ("@c.us" in user_id or "@g.us" in user_id)
        ):
            logger.info(f"[WhatsApp Plugin] Queuing WhatsApp reply for {user_id}: {reply[:60]}...")
            return {
                "action": "send_whatsapp_reply",
                "chat_id": user_id,
                "reply_text": reply,
                "platform": "whatsapp",
            }
        return None

    def on_purchase_detected(
        self, user_id: str, product_code: str, details: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Hook: Triggered when a purchase is detected.
        Sends a confirmation message via WhatsApp if applicable.
        """
        det = details or {}
        if det.get("source") == "whatsapp" or (
            user_id and ("@c.us" in user_id or "@g.us" in user_id)
        ):
            product_name = det.get("product_name", product_code)
            confirmation_msg = (
                f" تم تأكيد طلبك بنجاح!\n\n"
                f" المنتج: {product_name}\n"
                f" الكود: {product_code}\n\n"
                f"هنتواصل مع حضرتك قريب لتأكيد تفاصيل الشحن. "
                f"شكراً لثقتك فينا! "
            )
            logger.info(f"[WhatsApp Plugin] Purchase confirmation for {user_id}: {product_code}")
            return {
                "action": "send_whatsapp_confirmation",
                "chat_id": user_id,
                "confirmation_text": confirmation_msg,
                "product_code": product_code,
                "platform": "whatsapp",
            }
        return None

    def get_ui_snippet(self) -> Optional[str]:
        """Inject WhatsApp status badge and icon into dashboard."""
        return '''
        <div class="whatsapp-status-badge" style="display:inline-flex; align-items:center; gap:8px; background:rgba(37, 211, 102, 0.12); border:1px solid rgba(37, 211, 102, 0.35); color:#25d366; padding:5px 12px; border-radius:22px; font-size:0.8rem; font-weight:600; cursor:pointer;" onclick="window.location.hash='#whatsapp'" title="إضافة واتساب OpenWA">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="flex-shrink:0;">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
            </svg>
            <span>واتساب OpenWA</span>
            <span id="waStatusDot" style="display:inline-block; width:7px; height:7px; background:#888; border-radius:50%; box-shadow:0 0 6px #888; transition: all 0.3s;"></span>
        </div>
        <script>
        (function() {
            async function checkWAStatus() {
                try {
                    const res = await fetch('/api/whatsapp/status');
                    const data = await res.json();
                    const dot = document.getElementById('waStatusDot');
                    if (dot) {
                        if (data.is_connected) {
                            dot.style.background = '#25d366';
                            dot.style.boxShadow = '0 0 8px #25d366';
                        } else if (data.has_qr) {
                            dot.style.background = '#f59e0b';
                            dot.style.boxShadow = '0 0 8px #f59e0b';
                        } else {
                            dot.style.background = '#888';
                            dot.style.boxShadow = '0 0 6px #888';
                        }
                    }
                } catch(e) {}
            }
            checkWAStatus();
            setInterval(checkWAStatus, 15000);
        })();
        </script>
        '''
