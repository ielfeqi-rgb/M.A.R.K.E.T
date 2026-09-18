import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from cachetools import TTLCache
import httpx

from settings import settings
from excel_helper import excel_cache
from qr_detector import detect_qr_code
from ai_provider import AIProviderManager
from http_client import AsyncHTTPClient

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "ai_provider": "ollama",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2:3b",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "openai_base_url": "https://api.openai.com/v1",
    "groq_api_key": "",
    "groq_model": "llama-3.3-70b-versatile",
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    "custom_ai_url": "http://localhost:1234/v1",
    "custom_ai_key": "",
    "custom_ai_model": "local-model",
    "fb_page_token": "",
    "fb_verify_token": "change_me_in_production",
    "fb_app_secret": "",
    "auto_reply_comments": True,
    "comment_reply_mode": "both",  # "public", "private", "both"
    "ngrok_authtoken": "",
    "excel_path": "products.xlsx",
    "whatsapp_enabled": False,
    "whatsapp_openwa_url": "http://localhost:2785",
    "whatsapp_openwa_api_key": "",
    "whatsapp_session_id": "market-bot",
    "whatsapp_auto_reply": True,
    "whatsapp_send_purchase_confirmation": True,
    "system_prompt": (
        "أنت موظف خدمة عملاء مصري ودود ولطيف جداً في صفحة بيع ملابس. "
        "مهمتك هي الرد على استفسار العميل بالعامية المصرية الودية والمهذبة جداً. "
        "تحدث كبشر حقيقي تماماً وتجنب الكلمات الرسمية الجافة أو المصطلحات البرمجية. "
        "استخدم بيانات المنتج المرفقة لتنسيق رد جذاب ومقنع للعميل لمساعدته في الشراء. "
        "إذا سأل العميل عن السعر أو المقاس، أخبره بالتفاصيل المتاحة فقط بلغة لطيفة وبسيطة. "
        "لا تذكر أبداً أي رموز مثل كود المنتج للعميل، بل قل اسمه والمقاس واللون بوضوح. "
        "أهم شيء: لا تذكر أبداً أنك ذكاء اصطناعي أو بوت."
    ),
    "comment_prompt": (
        "أنت موظف خدمة عملاء مصري ودود ترد على تعليقات العملاء في بوستات فيسبوك. "
        "قم بكتابة رد قصير ومهذب جداً بالعامية المصرية (سطر واحد فقط) للترحيب بالعميل وإخباره أن التفاصيل كاملة والسعر تم إرسالهم في رسالة خاصة على الخاص (Inbox)."
    )
}

conversation_history: TTLCache[str, List[Dict[str, str]]] = TTLCache(
    maxsize=10000,
    ttl=settings.history_ttl_seconds
)

processed_messages_cache: TTLCache[str, bool] = TTLCache(
    maxsize=10000,
    ttl=600
)

processed_comments_cache: TTLCache[str, bool] = TTLCache(
    maxsize=10000,
    ttl=3600
)


@dataclass
class ProductInfo:
    code: str
    name: str
    price: float
    size: str
    color: str
    quantity: int
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "كود المنتج": self.code,
            "اسم المنتج": self.name,
            "السعر": self.price,
            "المقاس": self.size,
            "اللون": self.color,
            "الكمية المتاحة": self.quantity,
            "الوصف": self.description
        }


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                config.setdefault(k, v)
            return config
        except Exception as e:
            logger.error(f"Config load error: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(config_data: Dict[str, Any]) -> bool:
    try:
        current = load_config()
        current.update(config_data)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=4)
        logger.info("Settings saved successfully to config.json")
        return True
    except Exception as e:
        logger.error(f"Config save error: {e}")
        return False


async def get_fb_client() -> httpx.AsyncClient:
    try:
        http = await AsyncHTTPClient.get_instance()
        return http.general
    except Exception:
        return httpx.AsyncClient(timeout=15.0)


def update_history(sender_id: str, role: str, content: str):
    if sender_id not in conversation_history:
        conversation_history[sender_id] = []

    conversation_history[sender_id].append({"role": role, "content": content})

    if len(conversation_history[sender_id]) > settings.history_max_messages:
        conversation_history[sender_id] = conversation_history[sender_id][-settings.history_max_messages:]


async def infer_product_code_from_text(user_text: str) -> Optional[str]:
    config = load_config()
    try:
        code = await AIProviderManager.generate_code_inference(user_text, config)
        if code:
            logger.info(f"AI inferred product code for '{user_text}': {code}")
            return code
    except Exception as e:
        logger.error(f"Code inference error: {e}")
    return None


def verify_and_guard_grounding(raw_reply: str, product_info: Optional[ProductInfo], user_message: str) -> str:
    """
    Strict Deterministic Grounding Guardrail (Zero-Hallucination Enforcer):
    1. If product is NOT in catalog (product_info is None):
       Strictly force refusal message. Never allow the LLM to confirm having uncataloged items.
    2. If product is in catalog:
       Validate price and stock availability truth.
    """
    if product_info is None:
        logger.warning(f"[GROUNDING GUARD] Product not in catalog. Enforcing strict refusal for query: '{user_message}'")
        return "أهلاً بحضرتك يا فندم في M.A.R.K.E.T! 🌸 المنتج المطلوب غير متوفر حالياً في المخزن، أو برجاء تزويدنا بكود الموديل المطلوب للتأكد من توفره. ✨"

    if not raw_reply:
        return f"أهلاً بحضرتك يا فندم! 🌸 {product_info.name} متوفر بسعر {product_info.price} ج.م مقاس {product_info.size}. تحت أمرك لأي استفسار! ✨"

    # If product IS found, ensure stock availability
    if product_info.quantity <= 0:
        return f"أهلاً بحضرتك يا فندم! 🌸 منتج '{product_info.name}' خلصان حالياً من المخزن وبيتجهز للدفعة القادمة قريباً جداً! ✨"

    return raw_reply


async def generate_ai_reply(
    sender_id: str,
    product_info: Optional[ProductInfo],
    user_message: str
) -> str:
    config = load_config()
    history = conversation_history.get(sender_id, [])

    if product_info:
        product_str = json.dumps(product_info.to_dict(), ensure_ascii=False, indent=2)
        system_instruction = (
            config["system_prompt"] + 
            f"\n\n[حقيقة المخزن المطلقة - ممنوع تجاوزها]:\n{product_str}\n"
            f"ممنوع تماماً ذكر أي سعر غير {product_info.price} ج.م أو مقاس غير {product_info.size}."
        )
    else:
        system_instruction = (
            config["system_prompt"] + 
            "\n\n[تنبيه مخزن]: لم يتم العثور على أي منتج مطابق في قاعدة البيانات. "
            "ممنوع تماماً تأليف أسعار أو مقاسات. أخبر العميل بلطف أن المنتج غير متوفر حالياً واطلب كود المنتج أو صورته."
        )

    messages = [{"role": "system", "content": system_instruction}]

    for h in history[:-1]:
        messages.append(h)

    messages.append({"role": "user", "content": user_message})

    try:
        reply = await AIProviderManager.complete_chat(messages, config, temperature=0.5)
        if reply:
            return verify_and_guard_grounding(reply, product_info, user_message)
    except Exception as e:
        logger.error(f"AI Chat error: {e}")

    # Fallback message
    logger.warning("Serving rule-based grounded fallback message.")
    if product_info:
        return (
            f"أهلاً بحضرتك يا فندم! 🌸 {product_info.name} متوفر بسعر {product_info.price} ج.م مقاس {product_info.size} ولون {product_info.color}. "
            f"تحت أمرك لتأكيد الطلب الآن! ✨"
        )
    return "أهلاً بحضرتك يا فندم! 🌸 المنتج المطلوب غير مسجل حالياً في المخزن، برجاء تزويدنا بكود المنتج أو صورته للتأكد. ✨"


async def generate_comment_public_reply(user_comment: str, product_info: Optional[ProductInfo]) -> str:
    """Generates a polite short public reply to a Facebook comment."""
    config = load_config()
    comment_prompt = config.get("comment_prompt", DEFAULT_CONFIG["comment_prompt"])

    prod_name = product_info.name if product_info else "المنتج"
    system_instruction = f"{comment_prompt}\nاسم المنتج المطلوب: {prod_name}"

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": f"تعليق العميل: \"{user_comment}\""}
    ]

    try:
        reply = await AIProviderManager.complete_chat(messages, config, temperature=0.6)
        if reply:
            return reply.replace('"', '').strip()
    except Exception as e:
        logger.error(f"Comment AI Reply error: {e}")

    return "تم الرد على حضرتك بكل التفاصيل والأسعار في رسالة خاصة بالماسنجر يا فندم! 📩✨"


async def send_fb_message(sender_id: str, text_content: str) -> bool:
    """Sends a private message to a user on Facebook Messenger."""
    config = load_config()
    token = config.get("fb_page_token", "") or settings.fb_page_token

    if not token:
        logger.warning("Facebook Page Access Token not configured")
        return False

    client = await get_fb_client()
    url = f"{settings.fb_api_url}/me/messages"
    params = {"access_token": token}
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": text_content}
    }

    for attempt in range(settings.fb_max_retries):
        try:
            response = await client.post(url, params=params, json=payload)
            if response.status_code == 200:
                logger.info(f"Message successfully sent to {sender_id}")
                return True
            else:
                logger.error(f"Facebook API error: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Facebook send error: {e}")

        if attempt < settings.fb_max_retries - 1:
            await asyncio.sleep(2 ** attempt)

    return False


async def reply_to_fb_comment(comment_id: str, message: str) -> bool:
    """Replies publicly to a Facebook post comment."""
    config = load_config()
    token = config.get("fb_page_token", "") or settings.fb_page_token

    if not token:
        logger.warning("Facebook Page Access Token not configured")
        return False

    client = await get_fb_client()
    url = f"{settings.fb_api_url}/{comment_id}/comments"
    params = {"access_token": token}
    payload = {"message": message}

    try:
        response = await client.post(url, params=params, json=payload)
        if response.status_code == 200:
            logger.info(f"Successfully posted public reply to comment {comment_id}")
            return True
        else:
            logger.error(f"Facebook Comment reply error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Facebook comment error: {e}")
    return False


async def send_private_reply_to_comment(comment_id: str, text_content: str) -> bool:
    """Sends a private message to the author of a specific comment."""
    config = load_config()
    token = config.get("fb_page_token", "") or settings.fb_page_token

    if not token:
        return False

    client = await get_fb_client()
    url = f"{settings.fb_api_url}/me/messages"
    params = {"access_token": token}
    payload = {
        "recipient": {"comment_id": comment_id},
        "message": {"text": text_content}
    }

    try:
        response = await client.post(url, params=params, json=payload)
        if response.status_code == 200:
            logger.info(f"Successfully sent private message for comment {comment_id}")
            return True
        else:
            logger.error(f"Facebook private comment reply error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Private comment send error: {e}")
    return False


async def download_image(url: str) -> Optional[bytes]:
    client = await get_fb_client()
    try:
        response = await client.get(url, timeout=settings.qr_timeout)
        if response.status_code == 200:
            return response.content
        logger.warning(f"Image download failed with HTTP status: {response.status_code}")
    except Exception as e:
        logger.error(f"Image download error: {e}")
    return None


def lookup_product(code: str) -> Optional[ProductInfo]:
    data = excel_cache.get_product(code)
    if data:
        return ProductInfo(
            code=str(data.get("كود المنتج", "")),
            name=str(data.get("اسم المنتج", "")),
            price=float(data.get("السعر", 0)),
            size=str(data.get("المقاس", "")),
            color=str(data.get("اللون", "")),
            quantity=int(data.get("الكمية المتاحة", 0)),
            description=str(data.get("الوصف", ""))
        )
    return None


async def send_whatsapp_message(chat_id: str, text_content: str, image_url: Optional[str] = None) -> bool:
    """Sends a WhatsApp message via OpenWA Gateway adapter."""
    config = load_config()
    openwa_url = config.get("whatsapp_openwa_url", settings.whatsapp_openwa_url)
    api_key = config.get("whatsapp_openwa_api_key", settings.whatsapp_openwa_api_key)
    session_id = config.get("whatsapp_session_id", settings.whatsapp_session_id)

    try:
        from plugins.whatsapp_openwa.adapter import WhatsAppAdapter
        adapter = WhatsAppAdapter(openwa_url=openwa_url, api_key=api_key, session_id=session_id)
        res = await adapter.send_message(chat_id, text_content, image_url=image_url)
        await adapter.shutdown()
        return res.get("status") == "success"
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return False


async def process_incoming_message(
    sender_id: str,
    message_text: str = "",
    image_url: Optional[str] = None,
    message_id: Optional[str] = None,
    channel: str = "auto"
) -> str:
    """Processes an incoming customer message across all channels (Facebook, WhatsApp, etc.)."""
    from plugin_manager import plugin_manager

    if message_id:
        if message_id in processed_messages_cache:
            logger.info(f"Message ID '{message_id}' already processed. Skipping duplicate.")
            return ""
        processed_messages_cache[message_id] = True

    # Detect channel
    if channel == "auto":
        is_whatsapp = ("@c.us" in sender_id or "@g.us" in sender_id)
        actual_channel = "whatsapp" if is_whatsapp else "facebook"
    else:
        actual_channel = channel

    user_input_display = message_text or "[صورة منتج]"
    update_history(sender_id, "user", user_input_display)

    # 1. Trigger Plugin Hook: on_message_received
    try:
        plugin_manager.trigger_message_hook(sender_id, user_input_display)
    except Exception as e:
        logger.warning(f"Plugin message hook error: {e}")

    product_code = None
    product_info = None

    if image_url:
        logger.info(f"Downloading image for QR detection: {image_url[:50]}...")
        image_bytes = await download_image(image_url)
        if image_bytes:
            product_code = await detect_qr_code(image_bytes)
            if product_code:
                logger.info(f"QR code detected: {product_code}")

    if not product_code and message_text:
        # 1. Try real fuzzy multi-attribute search across Excel catalog
        try:
            fuzzy_res = excel_cache.search_product_fuzzy(message_text, min_threshold=0.55)
            if fuzzy_res.get("product"):
                p_dict = fuzzy_res["product"]
                product_info = ProductInfo(
                    code=str(p_dict.get("كود المنتج", "")),
                    name=str(p_dict.get("اسم المنتج", "")),
                    price=float(p_dict.get("السعر", 0.0) or 0.0),
                    size=str(p_dict.get("المقاس", "")),
                    color=str(p_dict.get("اللون", "")),
                    quantity=int(p_dict.get("الكمية المتاحة", 1) or 1),
                    description=str(p_dict.get("الوصف", ""))
                )
                product_code = product_info.code
                logger.info(f"[EXCEL FUZZY] Match '{product_info.name}' (Code: {product_code}) with confidence: {fuzzy_res['confidence']}")
        except Exception as e:
            logger.warning(f"Fuzzy search error: {e}")

        # 2. If still not matched, attempt AI code inference as fallback
        if not product_code:
            product_code = await infer_product_code_from_text(message_text)
            if product_code:
                product_info = lookup_product(product_code)

    if product_info:
        logger.info(f"Product verified in inventory: {product_info.name}. Generating grounded AI reply...")
        reply_text = await generate_ai_reply(sender_id, product_info, user_input_display)
    else:
        logger.info("Product not in inventory, generating strict non-hallucinating reply...")
        reply_text = await generate_ai_reply(sender_id, None, user_input_display)

    metadata = {
        "channel": actual_channel,
        "product_code": product_code,
        "product_name": product_info.name if product_info else None,
        "has_image": bool(image_url),
    }

    # 2. Trigger Plugin Hook: on_reply_generated
    try:
        plugin_manager.trigger_reply_hook(sender_id, user_input_display, reply_text, metadata)
    except Exception as e:
        logger.warning(f"Plugin reply hook error: {e}")

    # 3. Trigger Plugin Hook: on_purchase_detected
    if product_code:
        purchase_keywords = ["شراء", "اشتري", "طلب", "حجز", "اريد", "عاوز", "ابعتلي", "شحن", "توصيل", "اوردر"]
        if any(kw in user_input_display.lower() for kw in purchase_keywords):
            try:
                plugin_manager.trigger_purchase_hook(sender_id, product_code, {
                    "source": actual_channel,
                    "channel": actual_channel,
                    "product_name": product_info.name if product_info else product_code,
                    "price": product_info.price if product_info else 0,
                })
            except Exception as e:
                logger.warning(f"Plugin purchase hook error: {e}")

    # Send reply via the correct channel
    if actual_channel == "whatsapp":
        await send_whatsapp_message(sender_id, reply_text)
    else:
        await send_fb_message(sender_id, reply_text)

    update_history(sender_id, "assistant", reply_text)

    return reply_text


async def process_incoming_comment(
    comment_id: str,
    post_id: str,
    comment_text: str,
    sender_id: str,
    sender_name: str = ""
) -> Dict[str, Any]:
    """
    Handles auto-replying to post comments:
    1. Public reply on comment.
    2. Private inbox message with details & pricing.
    """
    config = load_config()
    if not config.get("auto_reply_comments", True):
        logger.info("Comment auto-reply is disabled in settings.")
        return {"status": "disabled"}

    if comment_id in processed_comments_cache:
        logger.info(f"Comment ID '{comment_id}' already processed. Skipping.")
        return {"status": "duplicate"}
    processed_comments_cache[comment_id] = True

    logger.info(f"Processing comment from {sender_name} ({sender_id}): '{comment_text}'")

    # 1. Infer product from comment text
    product_code = await infer_product_code_from_text(comment_text)
    product_info = lookup_product(product_code) if product_code else None

    mode = config.get("comment_reply_mode", "both")

    # 2. Public Reply
    public_reply = None
    if mode in ("public", "both"):
        public_reply = await generate_comment_public_reply(comment_text, product_info)
        await reply_to_fb_comment(comment_id, public_reply)

    # 3. Private Message Reply
    private_reply = None
    if mode in ("private", "both"):
        user_input_display = comment_text
        private_reply = await generate_ai_reply(sender_id, product_info, user_input_display)
        # Try sending via comment private reply endpoint first
        sent_private = await send_private_reply_to_comment(comment_id, private_reply)
        if not sent_private:
            # Fallback to direct sender_id message
            await send_fb_message(sender_id, private_reply)

    return {
        "status": "success",
        "comment_id": comment_id,
        "product_found": product_info.name if product_info else None,
        "public_reply": public_reply,
        "private_reply": private_reply
    }