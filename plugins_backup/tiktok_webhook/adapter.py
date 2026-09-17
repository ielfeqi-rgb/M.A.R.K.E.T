# TikTok Shop Webhook Adapter (Python)
# Author: M.A.R.K.E.T. AI Systems

def process(input_data):
    msg = input_data.get("user_message", "")
    metadata = input_data.get("metadata", {}) or {}
    open_id = metadata.get("open_id", "tiktok_user_888")
    shop_id = metadata.get("shop_id", "shop_egypt_01")
    
    return {
        "status": "success",
        "plugin": "tiktok_webhook",
        "injected_context": f"[محول TikTok Shop - Python]:\n- OpenID العميل: {open_id}\n- متجر TikTok: {shop_id}\n- بروتوكول الإرسال: TikTok Business Messaging API",
        "system_instruction_override": "أنت مساعد مبيعات متجر تيك توك. أجوبة سريعة ومباشرة ومرحة تشجع على شراء المنتج ورؤية العروض الحالية.",
        "outbound_meta": {
            "recipient": {"open_id": open_id},
            "platform": "tiktok",
            "shop_id": shop_id
        }
    }
