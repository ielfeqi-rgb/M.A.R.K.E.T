"""
WhatsApp OpenWA Extension Backend (M.A.R.K.E.T v3)
=================================================
Exposes dedicated dynamic API endpoints for the extension:
- GET  /status
- POST /connect
- POST /disconnect
- GET  /qr
- POST /send
- POST /webhook
- POST /register-webhook
"""

import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from plugins.whatsapp_openwa.adapter import WhatsAppAdapter, WhatsAppMessage

logger = logging.getLogger(__name__)

# Dedicated FastAPI router for this extension
router = APIRouter()

_adapter_instance: Optional[WhatsAppAdapter] = None


def get_adapter() -> WhatsAppAdapter:
    """Get or create singleton adapter for this extension using isolated config."""
    global _adapter_instance
    import os

    # Load isolated config
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass

    # Fallback to global config if isolated doesn't exist yet
    if not config:
        root_config = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
        if os.path.exists(root_config):
            try:
                with open(root_config, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass

    openwa_url = config.get("whatsapp_openwa_url", "http://localhost:2785")
    api_key = config.get("whatsapp_openwa_api_key", "")
    session_id = config.get("whatsapp_session_id", "market-bot")

    if _adapter_instance is None:
        _adapter_instance = WhatsAppAdapter(
            openwa_url=openwa_url,
            api_key=api_key,
            session_id=session_id
        )
    else:
        _adapter_instance.client.base_url = openwa_url.rstrip("/")
        _adapter_instance.client.api_key = api_key
        _adapter_instance.session_id = session_id

    return _adapter_instance


def on_config_updated(new_config: Dict[str, Any]):
    """Hook called by ExtensionEngineV3 when extension settings are updated."""
    global _adapter_instance
    if _adapter_instance:
        if "whatsapp_openwa_url" in new_config:
            _adapter_instance.client.base_url = new_config["whatsapp_openwa_url"].rstrip("/")
        if "whatsapp_openwa_api_key" in new_config:
            _adapter_instance.client.api_key = new_config["whatsapp_openwa_api_key"]
        if "whatsapp_session_id" in new_config:
            _adapter_instance.session_id = new_config["whatsapp_session_id"]
    logger.info("[WhatsApp Extension] Configuration reloaded in memory")


@router.get("/status")
async def ext_whatsapp_status():
    """Get current WhatsApp connection status."""
    adapter = get_adapter()
    return await adapter.get_status()


@router.post("/connect")
async def ext_whatsapp_connect():
    """Start or connect WhatsApp session."""
    adapter = get_adapter()
    return await adapter.connect()


@router.post("/disconnect")
async def ext_whatsapp_disconnect():
    """Disconnect WhatsApp session."""
    adapter = get_adapter()
    return await adapter.disconnect()


@router.get("/qr")
async def ext_whatsapp_qr():
    """Get QR code for web pairing."""
    adapter = get_adapter()
    return await adapter.get_qr()


@router.post("/send")
async def ext_whatsapp_send(data: dict):
    """Send text or image message."""
    phone = data.get("phone", data.get("chat_id", "")).strip()
    text = data.get("message", data.get("text", "")).strip()
    image_url = data.get("image_url", "").strip() or None

    if not phone:
        raise HTTPException(status_code=400, detail="رقم الهاتف مطلوب")
    if not text and not image_url:
        raise HTTPException(status_code=400, detail="نص الرسالة أو رابط الصورة مطلوب")

    adapter = get_adapter()
    result = await adapter.send_message(phone, text, image_url=image_url)
    if result.get("status") == "success":
        return result
    raise HTTPException(status_code=400, detail=result.get("message", "فشل الإرسال"))


@router.post("/webhook")
async def ext_whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """Incoming webhook from OpenWA."""
    try:
        raw_body = await request.body()
        payload = json.loads(raw_body.decode("utf-8"))

        adapter = get_adapter()
        msg = adapter.parse_webhook_event(payload)

        if msg:
            from bot_logic import process_incoming_message
            background_tasks.add_task(
                process_incoming_message,
                sender_id=msg.chat_id,
                message_text=msg.text,
                image_url=msg.media_url,
                message_id=msg.message_id,
                channel="whatsapp"
            )
            return {"status": "success", "event": "message_queued"}

        return {"status": "success", "event": payload.get("event", "status_processed")}
    except Exception as e:
        logger.error(f"[WhatsApp Webhook Error]: {e}")
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(e)})


@router.post("/register-webhook")
async def ext_whatsapp_register_webhook(data: Optional[dict] = None):
    """Register webhook target with OpenWA."""
    target_url = (data or {}).get("webhook_url")
    if not target_url:
        raise HTTPException(status_code=400, detail="رابط الـ webhook مطلوب")
    adapter = get_adapter()
    return await adapter.register_webhook(target_url)
