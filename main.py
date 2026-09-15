import asyncio
import hmac
import hashlib
import json
import logging
import os
import socket
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any

from fastapi import FastAPI, Request, Response, HTTPException, UploadFile, File, BackgroundTasks, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pyngrok import ngrok, conf
import uvicorn

from settings import settings
from logging_config import setup_logging
from bot_logic import (
    process_incoming_message,
    process_incoming_comment,
    load_config,
    save_config,
    generate_ai_reply,
    lookup_product,
)
from excel_helper import excel_cache
from http_client import close_all_clients, AsyncHTTPClient
from qr_detector import shutdown_executor as shutdown_qr_executor
from ai_provider import AIProviderManager
from hardware_detector import get_system_hardware
from llamacpp_manager import llama_manager
from plugin_manager import plugin_manager

setup_logging()
logger = logging.getLogger(__name__)

LOG_QUEUE: asyncio.Queue = asyncio.Queue()
WEBHOOK_URL: str | None = None
_shutdown_event = asyncio.Event()


class BroadcastQueueHandler(logging.Handler):
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.queue = queue
        self.loop = loop

    def emit(self, record: logging.LogRecord):
        try:
            msg = record.getMessage()
            if record.exc_info:
                msg += "\n" + self.formatException(record.exc_info)
            sender = record.name.split(".")[-1].capitalize()
            if record.levelno >= logging.ERROR:
                sender = "Error"
            elif sender in ("Root", "Main", "__main__"):
                sender = "System"

            log_data = {"sender": sender, "message": msg, "level": record.levelname}
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.queue.put_nowait, log_data)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global WEBHOOK_URL

    loop = asyncio.get_running_loop()
    queue_handler = BroadcastQueueHandler(LOG_QUEUE, loop)
    queue_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(queue_handler)

    logger.info("Starting M.A.R.K.E.T (OmniContext AI v%s)", settings.app_version)

    # Initialize shared HTTP pool
    await AsyncHTTPClient.get_instance()
    logger.info("Shared HTTP client pool initialized")

    config = load_config()
    ngrok_token = config.get("ngrok_authtoken", "").strip() or settings.ngrok_authtoken
    if ngrok_token:
        WEBHOOK_URL = await start_ngrok_tunnel(ngrok_token)
    else:
        logger.info("Ngrok authtoken not configured (running in local network mode)")

    excel_cache.reload()
    logger.info("Excel product database loaded")

    # Detect hardware at startup
    hw = get_system_hardware()
    logger.info("Hardware detected: %s RAM, %d cores (%s)", f"{hw['ram_total_gb']}GB", hw['cpu_cores'], hw['tier_label'])

    yield

    logger.info("Shutting down OmniContext AI...")
    _shutdown_event.set()

    # Automatically stop llama-server process if running
    try:
        llama_manager.stop()
        logger.info("Local llama-server process stopped cleanly")
    except Exception as e:
        logger.warning(f"Error stopping llama-server: {e}")

    await close_all_clients()
    shutdown_qr_executor()

    if ngrok_token:
        try:
            ngrok.kill()
            logger.info("Ngrok tunnel closed")
        except Exception as e:
            logger.warning(f"Error closing ngrok: {e}")

    logger.info("Shutdown complete")


app = FastAPI(
    title="M.A.R.K.E.T (OmniContext AI 2.0 Dashboard & Bot)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def log_message(sender: str, message: str):
    log_data = {"sender": sender, "message": message}
    logger.info(f"[{sender}] {message}")
    await LOG_QUEUE.put(log_data)


async def start_ngrok_tunnel(authtoken: str) -> str | None:
    try:
        ngrok.kill()
        conf.get_default().auth_token = authtoken
        tunnel = ngrok.connect(settings.port, proto="http", bind_tls=True)
        webhook_url = tunnel.public_url + "/webhook"
        await log_message("System", f"Ngrok public tunnel active: {webhook_url}")
        return webhook_url
    except Exception as e:
        await log_message("Error", f"Ngrok failed to connect: {e}")
        return None


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ---------------- System & Hardware APIs ----------------

@app.get("/health")
async def health_check():
    config = load_config()
    products_count = len(excel_cache.get_all_codes())
    hw = get_system_hardware()
    return {
        "status": "healthy",
        "app_name": "OmniContext AI",
        "version": "2.0.0",
        "webhook_url": WEBHOOK_URL,
        "excel_products": products_count,
        "ai_provider": config.get("ai_provider", "ollama"),
        "local_ip": get_local_ip(),
        "hardware_tier": hw["tier"],
    }


@app.get("/api/status")
async def get_status():
    config = load_config()
    excel_count = len(excel_cache.get_all_codes())
    hw = get_system_hardware()
    return {
        "running": True,
        "webhook_url": WEBHOOK_URL,
        "excel_products": excel_count,
        "local_ip": get_local_ip(),
        "config": config,
        "hardware": hw,
    }


@app.get("/api/hardware")
async def get_hardware_info():
    """Returns detected system specs & dynamically filtered model recommendations."""
    return get_system_hardware()


@app.get("/api/settings")
async def get_settings():
    return load_config()


@app.post("/api/server/reload_excel")
async def reload_excel_database():
    excel_cache.reload()
    count = len(excel_cache.get_all_codes())
    await log_message("System", f"Excel product database reloaded. Total products: {count}")
    return {"status": "success", "message": f"تم إعادة تحميل {count} منتج من شيت الإكسيل بنجاح"}


@app.post("/api/server/restart_ngrok")
async def restart_ngrok_endpoint():
    config = load_config()
    token = config.get("ngrok_authtoken", "").strip() or settings.ngrok_authtoken
    if not token:
        raise HTTPException(status_code=400, detail="توكن Ngrok غير محدد في الإعدادات")
    global WEBHOOK_URL
    WEBHOOK_URL = await start_ngrok_tunnel(token)
    if WEBHOOK_URL:
        return {"status": "success", "webhook_url": WEBHOOK_URL, "message": "تم إعادة تشغيل نفق Ngrok بنجاح"}
    raise HTTPException(status_code=500, detail="فشل إعداد نفق Ngrok")


@app.post("/api/server/shutdown")
async def shutdown_server_endpoint(background_tasks: BackgroundTasks):
    await log_message("System", "🛑 Server shutdown requested via UI OFF button.")
    
    def kill_server_process():
        time.sleep(1.0)
        logger.info("Terminating server process via UI OFF command...")
        try:
            llama_manager.stop()
        except Exception:
            pass
        os.kill(os.getpid(), 9)

    background_tasks.add_task(kill_server_process)
    return {"status": "success", "message": "تم إرسال أمر إيقاف الخادم والمحركات بنجاح"}


@app.post("/api/settings")
async def save_settings(settings_data: dict):
    success = save_config(settings_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save settings")

    ngrok_token = settings_data.get("ngrok_authtoken", "").strip() or settings.ngrok_authtoken
    if ngrok_token:
        global WEBHOOK_URL
        WEBHOOK_URL = await start_ngrok_tunnel(ngrok_token)

    await log_message("System", "Configuration updated successfully")
    return {"status": "success", "webhook_url": WEBHOOK_URL}


# ---------------- Plugin Manager & AI Plugin Generator APIs ----------------

@app.get("/api/plugins")
async def list_plugins_endpoint():
    return {"status": "success", "plugins": plugin_manager.list_plugins()}


@app.post("/api/plugins/toggle")
async def toggle_plugin_endpoint(data: dict):
    plugin_id = data.get("plugin_id")
    enabled = bool(data.get("enabled", True))
    if not plugin_id:
        raise HTTPException(status_code=400, detail="ID الإضافة مطلوب")
    plugin_manager.set_plugin_state(plugin_id, enabled)
    await log_message("PluginManager", f"Plugin '{plugin_id}' toggled to: {enabled}")
    return {"status": "success", "plugin_id": plugin_id, "enabled": enabled}


@app.post("/api/plugins/generate")
async def generate_ai_plugin_endpoint(data: dict):
    user_prompt = data.get("prompt", "").strip()
    if not user_prompt:
        raise HTTPException(status_code=400, detail="وصف الإضافة المطلوبة فارغ")

    await log_message("AIPluginGenerator", f"Generating new Python plugin via AI model for: {user_prompt}")
    config = load_config()

    system_instruction = """
[CONTEXT & SYSTEM ARCHITECTURE]
You are an expert Python software engineer for the M.A.R.K.E.T AI Engine (OmniContext v2.0).
M.A.R.K.E.T is an intelligent customer service & e-commerce automation platform built with Python FastAPI, local LLMs (llama.cpp / Qwen 2.5), Excel inventory database, and Meta Facebook Messenger/Feed integrations.

[PLUGIN SPECIFICATION]
You are generating a standalone single-file Python plugin for the M.A.R.K.E.T plugin system located in `plugins/`.
Every plugin MUST define a class named `Plugin` inheriting from `BasePlugin`.

Required Class Structure & Attributes:
```python
import os
import json
import logging
from typing import Dict, Any, Optional
from plugin_manager import BasePlugin

class Plugin(BasePlugin):
    plugin_id = "custom_plugin_id"  # Unique ID (lowercase alphanumeric + underscores)
    name = "اسم الإضافة"  # Arabic title
    description = "وصف تفصيلي لوظيفة الإضافة"
    version = "1.0.0"
    author = "Local AI Generator"
    enabled = True

    def on_message_received(self, user_id: str, message: str) -> Optional[Dict[str, Any]]:
        # Triggered when customer sends a message
        return None

    def on_reply_generated(self, user_id: str, prompt: str, reply: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        # Triggered when AI reply is generated
        return None

    def on_purchase_detected(self, user_id: str, product_code: str, details: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        # Triggered when purchase / order is detected
        return None

    def get_ui_snippet(self) -> Optional[str]:
        # Optional: Return HTML/CSS snippet to render custom visual icons or elements in the dashboard UI
        return None
```

[IMPORTANT INSTRUCTIONS]
1. Write 100% syntactically valid Python 3 code.
2. If the user request is related to UI elements, visual badges, or custom icons, implement `get_ui_snippet(self)` returning valid HTML/CSS strings so it renders dynamically in the dashboard.
3. OUTPUT ONLY THE EXECUTABLE PYTHON CODE inside a single markdown code block (` ```python ... ``` `). Do NOT include conversational text outside the code block.
"""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": f"وصف الإضافة المطلوبة: {user_prompt}"}
    ]

    try:
        raw_reply = await AIProviderManager.complete_chat(messages, config, temperature=0.3)
        if not raw_reply:
            raise HTTPException(status_code=500, detail="لم يتلقّ الخادم رد من نموذج الذكاء الاصطناعي (تأكد من اختيار وتأكيد المزود في الإعدادات أو تشغيل llama-server)")

        # Extract python code block
        code = raw_reply.strip()
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            parts = code.split("```")
            if len(parts) >= 2:
                code = parts[1].strip()

        # Fallback safeguard if model output lacks Plugin class
        if "class Plugin(" not in code:
            import re
            safe_clean_id = re.sub(r'[^a-zA-Z0-9_]', '', user_prompt.lower().replace(" ", "_"))[:20] or "custom_ai_plugin"
            code = f'''import logging
from typing import Dict, Any, Optional
from plugin_manager import BasePlugin

class Plugin(BasePlugin):
    plugin_id = "{safe_clean_id}"
    name = "إضافة مخصصة: {user_prompt[:25]}"
    description = "{user_prompt}"
    version = "1.0.0"
    author = "Local AI Generator"
    enabled = True

    def on_reply_generated(self, user_id: str, prompt: str, reply: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        logging.info(f"[{safe_clean_id}] Triggered for prompt: {{prompt}}")
        return {{"status": "active", "prompt": prompt}}
'''

        # Generate safe plugin filename
        import re, time
        clean_prompt_words = re.sub(r'[^a-zA-Z0-9_]', '', user_prompt.lower().replace(" ", "_"))
        if not clean_prompt_words or clean_prompt_words.strip("_") == "":
            safe_id = f"custom_plugin_{int(time.time())}"
        else:
            safe_id = clean_prompt_words[:20].strip("_") or f"custom_plugin_{int(time.time())}"

        filename = f"ai_{safe_id}.py"
        plugins_folder = os.path.join(os.path.dirname(__file__), "plugins")
        os.makedirs(plugins_folder, exist_ok=True)
        plugin_filepath = os.path.join(plugins_folder, filename)

        with open(plugin_filepath, "w", encoding="utf-8") as f:
            f.write(code)

        # Reload plugins
        plugin_manager.load_plugins()
        await log_message("AIPluginGenerator", f"New plugin saved to plugins/{filename} and loaded successfully!")

        return {
            "status": "success",
            "file_name": filename,
            "filename": filename,
            "message": f"تم توليد كود الإضافة وحفظها في plugins/{filename} بنجاح! 🎉",
            "plugins": plugin_manager.list_plugins()
        }
    except Exception as e:
        logger.error(f"Plugin generation error: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في توليد الإضافة: {str(e)}")


# ---------------- llama.cpp Native Process Control APIs ----------------

@app.get("/api/llamacpp/status")
async def get_llamacpp_status():
    return llama_manager.get_status()


@app.post("/api/llamacpp/install")
async def install_llamacpp_engine():
    res = llama_manager.trigger_install()
    if res.get("success"):
        await log_message("LlamaEngine", "Started background installation of llama.cpp")
    return res


@app.post("/api/llamacpp/start")
async def start_llamacpp_engine(data: dict):
    model = data.get("model_filename", "").strip()
    threads = int(data.get("threads", 4))
    context_size = int(data.get("context_size", 4096))
    port = int(data.get("port", 8081))

    if not model:
        raise HTTPException(status_code=400, detail="اسم ملف الموديل (.gguf) مطلوب")

    res = llama_manager.start(model_filename=model, threads=threads, context_size=context_size, port=port)
    if res.get("success"):
        await log_message("LlamaEngine", f"llama-server started on port {port} with model {model}")
    return res


@app.post("/api/llamacpp/stop")
async def stop_llamacpp_engine():
    res = llama_manager.stop()
    await log_message("LlamaEngine", "llama-server stopped")
    return res


# ---------------- AI Models Management API ----------------

@app.get("/api/models/local")
async def list_local_models():
    config = load_config()
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    models = await AIProviderManager.get_ollama_models(ollama_url)
    return {"status": "success", "models": models}


@app.post("/api/models/pull")
async def pull_model(data: dict):
    model_name = data.get("model_name", "").strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name is required")

    config = load_config()
    ollama_url = config.get("ollama_url", "http://localhost:11434")

    async def event_stream():
        async for progress in AIProviderManager.pull_ollama_model(model_name, ollama_url):
            yield f"data: {json.dumps(progress)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/models/test")
async def test_ai_model(data: Optional[dict] = None):
    config = load_config()
    if data and isinstance(data, dict):
        config.update(data)
    result = await AIProviderManager.test_provider(config)
    return result


@app.post("/api/test/chat")
async def test_chat(data: dict):
    user_message = data.get("message", "").strip()
    product_code = data.get("product_code", "").strip()

    if not user_message and not product_code:
        raise HTTPException(status_code=400, detail="Message or product code is required")

    product_info = lookup_product(product_code) if product_code else None
    reply = await generate_ai_reply("test_dashboard_user", product_info, user_message or "تفاصيل المنتج")
    return {"status": "success", "reply": reply, "product_found": product_info.name if product_info else None}


# ---------------- Products CRUD & Excel API ----------------

@app.get("/api/products")
async def get_products():
    products = excel_cache.get_all_products()
    return {"status": "success", "count": len(products), "products": products}


@app.post("/api/products")
async def save_product(product: dict):
    if not product.get("كود المنتج"):
        raise HTTPException(status_code=400, detail="كود المنتج مطلوب")

    success = excel_cache.add_or_update_product(product)
    if success:
        await log_message("Excel", f"Product updated: {product.get('كود المنتج')}")
        return {"status": "success", "message": "تم حفظ المنتج بنجاح"}
    raise HTTPException(status_code=500, detail="فشل حفظ المنتج في شيت الإكسيل")


@app.delete("/api/products/{code}")
async def delete_product(code: str):
    success = excel_cache.delete_product(code)
    if success:
        await log_message("Excel", f"Product deleted: {code}")
        return {"status": "success", "message": f"تم حذف المنتج {code}"}
    raise HTTPException(status_code=404, detail="المنتج غير موجود")


@app.post("/api/excel/upload")
async def upload_excel(file: UploadFile = File(...)):
    config = load_config()
    target_path = config.get("excel_path", "products.xlsx")

    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    try:
        contents = await file.read()
        with open(target_path, "wb") as f:
            f.write(contents)
        excel_cache.reload()
        await log_message("Excel", f"Excel sheet uploaded: {file.filename}")
        return {"status": "success", "message": "تم رفع وتحديث شيت المنتجات بنجاح"}
    except Exception as e:
        await log_message("Error", f"Excel upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/excel/template")
async def download_excel_template():
    config = load_config()
    target_path = config.get("excel_path", "products.xlsx")
    excel_cache.create_template(target_path)

    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Template not found")

    return FileResponse(
        path=target_path,
        filename="products_template.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------- Logs Stream API ----------------

@app.get("/api/logs/stream")
async def stream_logs():
    async def log_generator():
        while not _shutdown_event.is_set():
            try:
                while not LOG_QUEUE.empty():
                    log_data = await LOG_QUEUE.get()
                    yield f"data: {json.dumps(log_data)}\n\n"
                await asyncio.sleep(0.5)
            except (asyncio.CancelledError, Exception):
                break

    return StreamingResponse(log_generator(), media_type="text/event-stream")


# ---------------- Facebook Webhook Routes ----------------

@app.get("/webhook")
async def verify_fb_webhook(request: Request):
    config = load_config()
    verify_token = config.get("fb_verify_token", settings.fb_verify_token)

    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == verify_token:
            await log_message("Facebook", "Webhook verified successfully by Meta")
            return Response(content=challenge, media_type="text/plain")
        else:
            await log_message("Error", "Facebook Verification token mismatch")
            raise HTTPException(status_code=403, detail="Token mismatch")
    raise HTTPException(status_code=400, detail="Missing parameters")


@app.post("/webhook")
async def receive_fb_event(request: Request, background_tasks: BackgroundTasks):
    try:
        raw_body = await request.body()
        body = json.loads(raw_body.decode("utf-8"))

        if body.get("object") != "page":
            raise HTTPException(status_code=404, detail="Not a page subscription")

        for entry in body.get("entry", []):
            # 1. Messenger Direct Messages
            for event in entry.get("messaging", []):
                if "message" not in event:
                    continue

                sender_id = event["sender"]["id"]
                message_data = event["message"]
                message_id = message_data.get("mid")
                message_text = message_data.get("text", "")
                image_url = None

                for attachment in message_data.get("attachments", []):
                    if attachment.get("type") == "image":
                        image_url = attachment.get("payload", {}).get("url")
                        break

                background_tasks.add_task(
                    process_message_background,
                    sender_id,
                    message_text,
                    image_url,
                    message_id
                )

            # 2. Facebook Feed / Comments Events
            for change in entry.get("changes", []):
                if change.get("field") == "feed":
                    val = change.get("value", {})
                    item = val.get("item")
                    verb = val.get("verb")

                    # When a new comment is added to a post
                    if item == "comment" and verb == "add":
                        comment_id = val.get("comment_id")
                        post_id = val.get("post_id")
                        comment_text = val.get("message", "")
                        from_user = val.get("from", {})
                        sender_id = from_user.get("id")
                        sender_name = from_user.get("name", "")

                        # Ignore comments made by the page itself
                        page_id = entry.get("id")
                        if sender_id == page_id:
                            continue

                        background_tasks.add_task(
                            process_comment_background,
                            comment_id,
                            post_id,
                            comment_text,
                            sender_id,
                            sender_name
                        )

        return Response(content="EVENT_RECEIVED", status_code=200)

    except Exception as e:
        await log_message("Error", f"Webhook processing error: {e}")
        return Response(content="ERROR", status_code=500)


async def process_message_background(sender_id: str, message_text: str, image_url: str | None, message_id: str | None):
    try:
        user_input = message_text or "[Image received]"
        await log_message("Facebook", f"Incoming Messenger msg from {sender_id}: {user_input}")

        reply = await process_incoming_message(sender_id, message_text, image_url, message_id)
        if reply:
            await log_message("Bot", f"Replied to {sender_id}: {reply[:90]}...")
    except Exception as e:
        await log_message("Error", f"Message background processing error: {e}")


async def process_comment_background(comment_id: str, post_id: str, comment_text: str, sender_id: str, sender_name: str):
    try:
        await log_message("Facebook", f"Incoming Post Comment by {sender_name}: {comment_text}")
        res = await process_incoming_comment(comment_id, post_id, comment_text, sender_id, sender_name)
        if res.get("status") == "success":
            await log_message("Bot", f"Auto-replied to comment {comment_id} ({sender_name})")
    except Exception as e:
        await log_message("Error", f"Comment background processing error: {e}")


# ---------------- Static Files Dashboard Mounting ----------------

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


def main():
    config = uvicorn.Config(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=False,
        timeout_graceful_shutdown=3,
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    except (KeyboardInterrupt, SystemExit):
        logger.info("OmniContext AI server stopped cleanly.")


if __name__ == "__main__":
    main()