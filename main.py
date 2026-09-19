import asyncio
import hmac
import hashlib
import json
import logging
import os
from pathlib import Path
import socket
import time
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
    ProductInfo,
    verify_and_guard_grounding,
)
from excel_helper import excel_cache
from http_client import close_all_clients, AsyncHTTPClient
from qr_detector import shutdown_executor as shutdown_qr_executor
from ai_provider import AIProviderManager
from hardware_detector import get_system_hardware
from llamacpp_manager import llama_manager
from plugin_manager import plugin_manager

# WhatsApp adapter (initialized lazily on startup)
_whatsapp_adapter = None

setup_logging()
logger = logging.getLogger(__name__)

LOG_QUEUE: asyncio.Queue = asyncio.Queue()
WEBHOOK_URL: str | None = None
_shutdown_event = asyncio.Event()
SERVER_START_TIME = time.time()


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

    # Initialize SQLite WAL Storage Engine (ACID-compliant storage)
    from database import db
    synced_count = db.sync_from_excel()
    logger.info(f"SQLite WAL Storage Engine online: {synced_count} products synchronized.")

    # Detect hardware at startup
    hw = get_system_hardware()
    logger.info("Hardware detected: %s RAM, %d cores (%s)", f"{hw['ram_total_gb']}GB", hw['cpu_cores'], hw['tier_label'])

    # Initialize WhatsApp adapter if enabled
    global _whatsapp_adapter
    try:
        wa_config = config
        if wa_config.get("whatsapp_enabled", False):
            from plugins.whatsapp_openwa.adapter import WhatsAppAdapter
            _whatsapp_adapter = WhatsAppAdapter(
                openwa_url=wa_config.get("whatsapp_openwa_url", "http://localhost:2785"),
                api_key=wa_config.get("whatsapp_openwa_api_key", ""),
                session_id=wa_config.get("whatsapp_session_id", "market-bot"),
            )
            logger.info("WhatsApp OpenWA adapter initialized (session: %s)", wa_config.get("whatsapp_session_id", "market-bot"))
        else:
            logger.info("WhatsApp integration disabled in config (set whatsapp_enabled=true to activate)")
    except Exception as e:
        logger.warning(f"WhatsApp adapter initialization skipped: {e}")

    yield

    logger.info("Shutting down OmniContext AI...")
    _shutdown_event.set()

    # Shutdown WhatsApp adapter
    if _whatsapp_adapter:
        try:
            await _whatsapp_adapter.shutdown()
            logger.info("WhatsApp adapter shut down cleanly")
        except Exception as e:
            logger.warning(f"Error shutting down WhatsApp adapter: {e}")

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
    title="M.A.R.K.E.T (OmniContext AI 3.5 Scratch Lab Edition)",
    version="3.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all v3 dynamic extension routers into FastAPI app
plugin_manager.mount_extension_routers(app)


async def log_message(level: str, message: str, color: str = "text-slate-200"):
    log_data = {
        "level": level,
        "message": message,
        "color": color,
        "timestamp": time.strftime("%H:%M:%S")
    }
    logger.info(f"[{level}] {message}")
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
        "app_name": "M.A.R.K.E.T AI",
        "version": "3.5.0",
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
    base_dir = os.path.abspath(".")
    return {
        "running": True,
        "pid": os.getpid(),
        "uptime_seconds": int(time.time() - SERVER_START_TIME),
        "webhook_url": WEBHOOK_URL,
        "excel_products": excel_count,
        "local_ip": get_local_ip(),
        "base_dir": base_dir,
        "paths": {
            "config": os.path.join(base_dir, "config.json"),
            "excel": os.path.join(base_dir, config.get("excel_path", "products.xlsx")),
            "plugins": os.path.join(base_dir, "plugins"),
            "bin": os.path.join(base_dir, "bin"),
            "main": os.path.join(base_dir, "main.py"),
            "scratch_engine": os.path.join(base_dir, "scratch_engine.py"),
            "bot_logic": os.path.join(base_dir, "bot_logic.py"),
            "ai_provider": os.path.join(base_dir, "ai_provider.py"),
        },
        "plugins": plugin_manager.list_plugins(),
        "config": config,
        "hardware": hw,
    }


@app.get("/api/hardware")
async def get_hardware_info():
    """Returns detected system specs & dynamically filtered model recommendations."""
    return get_system_hardware()


@app.get("/api/settings")
async def get_settings():
    cfg = load_config()
    return {"status": "success", "config": cfg, **cfg}


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
    await log_message("System", " Server shutdown requested via UI OFF button.")
    
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
    if "ngrok_auth_token" in settings_data and not settings_data.get("ngrok_authtoken"):
        settings_data["ngrok_authtoken"] = settings_data["ngrok_auth_token"]
    elif "ngrok_authtoken" in settings_data and not settings_data.get("ngrok_auth_token"):
        settings_data["ngrok_auth_token"] = settings_data["ngrok_authtoken"]

    success = save_config(settings_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save settings")

    ngrok_token = settings_data.get("ngrok_authtoken", "").strip() or settings.ngrok_authtoken
    if ngrok_token:
        global WEBHOOK_URL
        WEBHOOK_URL = await start_ngrok_tunnel(ngrok_token)

    await log_message("System", "Configuration updated successfully")
    return {"status": "success", "webhook_url": WEBHOOK_URL}


@app.post("/api/test/telegram")
async def test_telegram_alert(payload: dict):
    """Sends a test error alert via Telegram bot to verify IT notification integration."""
    config = load_config()
    bot_token = (payload.get("bot_token") or config.get("telegram_bot_token", "")).strip()
    chat_id = (payload.get("chat_id") or config.get("telegram_chat_id", "")).strip()
    if not bot_token or not chat_id:
        raise HTTPException(status_code=400, detail="يجب توفير Bot Token و Chat ID أولاً")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": " [M.A.R.K.E.T IT Sentinel Alert]\n تجربة إرسال تنبيهات الأخطاء تعمل بنجاح تام من لوحة الإعدادات!",
                }
            )
            if resp.status_code == 200:
                await log_message("IT_Sentinel", "Telegram test notification sent successfully.")
                return {"status": "success", "message": "تم إرسال رسالة الاختبار بنجاح إلى تليجرام!"}
            else:
                return {"status": "error", "message": f"استجابة تليجرام ({resp.status_code}): {resp.text}"}
    except Exception as e:
        return {"status": "error", "message": f"فشل الاتصال بتليجرام: {str(e)}"}


@app.post("/api/test/openwa")
async def test_openwa_connection(payload: dict):
    """Checks connection health of the local/remote WhatsApp OpenWA gateway."""
    config = load_config()
    url = (payload.get("url") or config.get("whatsapp_openwa_url", "http://localhost:2785")).strip().rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/api/sessions/market-bot/status")
            return {"status": "success", "data": resp.json(), "message": "تم الاتصال ببوابة OpenWA بنجاح!"}
    except Exception as e:
        return {"status": "error", "message": f"تعذر الاتصال بـ OpenWA على {url}: {str(e)}"}


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


@app.delete("/api/plugins/{plugin_id}")
async def delete_plugin_endpoint(plugin_id: str):
    plugins_dir = Path(__file__).parent / "plugins"
    ext_dir = plugins_dir / plugin_id
    if ext_dir.exists() and ext_dir.is_dir():
        import shutil
        shutil.rmtree(ext_dir, ignore_errors=True)
        plugin_manager.load_plugins()
        await log_message("PluginManager", f"Deleted extension: {plugin_id}")
        return {"status": "success", "plugin_id": plugin_id, "message": f"تم حذف الإضافة '{plugin_id}' بنجاح"}
    raise HTTPException(status_code=404, detail="الإضافة غير موجودة")



@app.get("/api/v3/coder/status")
async def get_coder_model_status():
    """Reports status of the dedicated Qwen Coder 0.5B extension generator engine."""
    config = load_config()
    coder_model = config.get("coder_model", "qwen2.5-coder:0.5b")
    coder_url = config.get("coder_ollama_url", config.get("ollama_url", "http://localhost:11434"))

    # Check Ollama
    is_available = False
    try:
        models = await AIProviderManager.get_ollama_models(coder_url)
        is_available = any(coder_model in (m.get("name") or "") for m in models)
    except Exception:
        pass

    return {
        "status": "success",
        "coder_engine": "Qwen 2.5 Coder 0.5B",
        "model": coder_model,
        "endpoint": coder_url,
        "is_available_locally": is_available,
        "role": "مخصص حصرياً لبرمجة وتوليد إضافات v3 المستقلة (منفصل تماماً عن محرك المحادثات)",
        "chat_model_separated": True
    }


@app.post("/api/plugins/generate")
async def generate_ai_plugin_endpoint(data: dict):
    user_prompt = data.get("prompt", "").strip()
    if not user_prompt:
        raise HTTPException(status_code=400, detail="وصف الإضافة المطلوبة فارغ")

    await log_message("QwenCoder", f"Generating M.A.R.K.E.T v3 Extension via Qwen Coder for: {user_prompt}")
    config = load_config()

    system_instruction = """أنت مهندس إضافات خفيف ومباشر لنظام M.A.R.K.E.T.
المطلوب منك برمجة إضافة كاملة بناءً على طلب المستخدم بدقة تامة.
الإضافة تتكون حصراً من 3 ملفات، ويجب إخراج كل ملف في كود منفصل كالتالي:

### manifest.json
```json
{
  "manifest_version": 3,
  "id": "employee_manager",
  "name": "إدارة الموظفين",
  "version": "1.0.0",
  "description": "إضافة لعرض وتعديل أسماء وبيانات الموظفين",
  "icon": "users",
  "entrypoint": "backend.py",
  "permissions": ["ui"],
  "enabled": true,
  "ui": {
    "tab": {
      "id": "tab-employees",
      "title": "الموظفين",
      "icon": "users",
      "template": "ui/tab.html"
    }
  },
  "routes": {
    "prefix": "/ext/employee_manager"
  }
}
```

### backend.py
```python
from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# قائمة تخزين تجريبية أو بيانات
employees = [
    {"id": 1, "name": "أحمد محمود", "role": "مبيعات"},
    {"id": 2, "name": "سارة علي", "role": "خدمة عملاء"}
]

@router.get("/list")
async def get_employees():
    return {"status": "success", "employees": employees}

@router.post("/update")
async def update_employee(request: Request):
    data = await request.json()
    emp_id = data.get("id")
    new_name = data.get("name")
    for emp in employees:
        if emp["id"] == emp_id:
            emp["name"] = new_name
            return {"status": "success", "message": "تم تحديث الاسم بنجاح"}
    return {"status": "error", "message": "الموظف غير موجود"}
```

### ui/tab.html
```html
<div class="card glass-card p-4 space-y-4">
    <h2 class="text-base font-bold">قائمة الموظفين</h2>
    <div id="emp-list" class="space-y-2">
        <!-- يتم عرض الموظفين وتعديلهم هنا -->
    </div>
</div>
```

قواعد صارمة:
1. نفّذ المطلوب في طلب المستخدم بالتحديد مع كتابة كود بايثون وHTML متكامل وفعّال.
2. لا تستخدم أطر عمل ثقيلة خارجية.
3. أخرج الكود مباشرة بدون مقدمات أو خاتمة.
"""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": f"المطلوب برمجة هذه الإضافة بالكامل بالملفات الثلاثة: {user_prompt}"}
    ]

    try:
        # Generate code using the dedicated Qwen Coder model runner
        raw_reply = await AIProviderManager.complete_coder(messages, config, temperature=0.1)
        if not raw_reply:
            raise HTTPException(status_code=500, detail="تعذر الحصول على رد من محرك البرمجة Qwen Coder (تأكد من تشغيل Ollama أو تفعيل المزود في الإعدادات)")

        import re, time
        # Extract extension id or build safe id
        safe_id = re.sub(r'[^a-zA-Z0-9_]', '', user_prompt.lower().replace(" ", "_"))
        safe_id = safe_id[:18].strip("_") or f"ext_{int(time.time())}"

        # Parse files from model response using clean regex
        manifest_content = None
        backend_content = None
        tab_html_content = None

        m_match = re.search(r'###\s*(?:\d+\.\s*)?manifest\.json[\s\S]*?```(?:json)?\s*([\s\S]*?)```', raw_reply)
        if m_match:
            try:
                manifest_content = json.loads(m_match.group(1).strip())
                if isinstance(manifest_content, dict) and "id" in manifest_content and manifest_content["id"] not in ("employee_manager", "my_extension_id", ""):
                    safe_id = manifest_content["id"]
                elif isinstance(manifest_content, dict):
                    manifest_content["id"] = safe_id
                    manifest_content["routes"] = {"prefix": f"/ext/{safe_id}"}
                    if "ui" in manifest_content and "tab" in manifest_content["ui"]:
                        manifest_content["ui"]["tab"]["id"] = f"tab-{safe_id}"
            except Exception as e:
                logger.warning(f"Error parsing manifest.json: {e}")

        b_match = re.search(r'###\s*(?:\d+\.\s*)?backend\.py[\s\S]*?```(?:python)?\s*([\s\S]*?)```', raw_reply)
        if b_match:
            backend_content = b_match.group(1).strip()

        t_match = re.search(r'###\s*(?:\d+\.\s*)?(?:ui/)?tab\.html[\s\S]*?```(?:html)?\s*([\s\S]*?)```', raw_reply)
        if t_match:
            tab_html_content = t_match.group(1).strip()

        # If model returned a single python block without manifest tags, fallback gracefully
        if not backend_content:
            if "```python" in raw_reply:
                backend_content = raw_reply.split("```python")[1].split("```")[0].strip()
            elif "```" in raw_reply:
                parts = raw_reply.split("```")
                if len(parts) >= 2:
                    backend_content = parts[1].strip()
            else:
                backend_content = raw_reply.strip()

        # Build default manifest if none parsed
        if not manifest_content:
            manifest_content = {
                "manifest_version": 3,
                "id": safe_id,
                "name": f"إضافة: {user_prompt[:25]}",
                "version": "1.0.0",
                "description": user_prompt,
                "icon": "puzzle",
                "entrypoint": "backend.py",
                "permissions": ["network", "ui", "webhooks"],
                "enabled": True,
                "ui": {
                    "tab": {
                        "id": f"tab-{safe_id}",
                        "title": user_prompt[:18],
                        "icon": "puzzle",
                        "template": "ui/tab.html"
                    },
                    "settings_fields": [
                        {
                            "key": "enabled",
                            "label": "تفعيل الإضافة",
                            "type": "boolean",
                            "default": True
                        }
                    ]
                },
                "routes": {
                    "prefix": f"/ext/{safe_id}",
                    "webhooks": ["/webhook"]
                }
            }

        # Build default tab html if none parsed
        if not tab_html_content:
            tab_html_content = f'''<div class="card glass-card p-4">
    <div class="d-flex align-items-center gap-3 mb-3">
        <div style="width:40px; height:40px; border-radius:10px; background:var(--primary); display:flex; align-items:center; justify-content:center; color:white;">
            <i data-lucide="puzzle"></i>
        </div>
        <div>
            <h2 class="m-0">{manifest_content.get("name", safe_id)}</h2>
            <p class="text-muted small m-0">{user_prompt}</p>
        </div>
    </div>
    <div class="alert alert-info">
        تم توليد هذه الإضافة وتثبيتها بنجاح عبر محرك Qwen 2.5 Coder 0.5B المخصص.
    </div>
</div>'''

        # Ensure router exists in backend code
        if "APIRouter" not in backend_content:
            backend_content = f"""from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status")
async def get_status():
    return {{"status": "ok", "extension": "{safe_id}"}}

@router.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.json()
    logger.info(f"[{safe_id}] Webhook data: {{body}}")
    return {{"status": "success", "received": True}}

{backend_content}
"""

        # Automated syntax validation and repair loop
        try:
            compile(backend_content, "backend.py", "exec")
        except SyntaxError as syn_err:
            err_msg = f"SyntaxError on line {syn_err.lineno}: {syn_err.msg}"
            await log_message("QwenCoder", f"[Feedback Loop]  Generated backend.py has {err_msg}. Triggering repair via omni_engine...")
            repair_messages = [
                {"role": "system", "content": "You are a code fixer. Fix the exact syntax error and output ONLY the complete corrected Python code inside a markdown block. No explanations."},
                {"role": "user", "content": f"The following backend.py code has an error:\n```python\n{backend_content}\n```\nError: {err_msg}\nPlease fix the error and return the full working code."}
            ]
            repair_res = await AIProviderManager.complete_coder(repair_messages, config, temperature=0.1)
            if repair_res and "```" in repair_res:
                parts = repair_res.split("```")
                if len(parts) >= 2:
                    fixed_code = parts[1].strip()
                    lines = fixed_code.split("\n", 1)
                    if len(lines) > 1 and lines[0].strip() == "python":
                        fixed_code = lines[1].strip()
                    try:
                        compile(fixed_code, "backend.py", "exec")
                        backend_content = fixed_code
                        await log_message("QwenCoder", f"[Feedback Loop]  omni_engine successfully auto-repaired backend.py!")
                    except Exception:
                        pass

        # Save into plugins/<safe_id>/
        ext_folder = os.path.join(os.path.dirname(__file__), "plugins", safe_id)
        os.makedirs(ext_folder, exist_ok=True)
        ui_folder = os.path.join(ext_folder, "ui")
        os.makedirs(ui_folder, exist_ok=True)

        with open(os.path.join(ext_folder, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest_content, f, ensure_ascii=False, indent=2)

        with open(os.path.join(ext_folder, "backend.py"), "w", encoding="utf-8") as f:
            f.write(backend_content)

        with open(os.path.join(ui_folder, "tab.html"), "w", encoding="utf-8") as f:
            f.write(tab_html_content)

        # Reload plugins and dynamically mount routes into running FastAPI
        plugin_manager.load_plugins()
        plugin_manager.mount_extension_routers(app)
        await log_message("QwenCoder", f"Extension '{safe_id}' created and mounted successfully under /ext/{safe_id}")

        return {
            "status": "success",
            "extension_id": safe_id,
            "manifest": manifest_content,
            "message": f"تمت برمجة وتثبيت إضافة v3 الكاملة ({manifest_content.get('name')}) في plugins/{safe_id}/ وتفعيلها فورياً! ",
            "schema": plugin_manager.get_ui_schema()
        }
    except Exception as e:
        logger.error(f"Plugin generation error: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في توليد وبرمجة الإضافة: {str(e)}")


@app.post("/api/plugins/reload")
async def reload_plugins_endpoint():
    """Hot-reloads all plugins (single-file and channel directories) from disk."""
    plugin_manager.load_plugins()
    plugin_manager.mount_extension_routers(app)
    count = len(plugin_manager.plugins) + len(plugin_manager.channel_plugins)
    await log_message("PluginManager", f"Reloaded all plugins from disk. Total loaded: {count}")
    return {
        "status": "success",
        "message": f"تم إعادة تحميل {count} إضافة بنجاح",
        "plugins": plugin_manager.list_plugins(),
        "channels": plugin_manager.get_channel_plugins()
    }


@app.get("/api/channels")
async def list_channels_endpoint():
    """Returns all available communication channel plugins (WhatsApp, Telegram, Messenger, etc.)."""
    return {
        "status": "success",
        "channels": plugin_manager.get_channel_plugins()
    }


# ---------------- V3 Chrome-like Extension APIs ----------------

@app.get("/api/v3/ui/schema")
async def get_v3_ui_schema_endpoint():
    """Returns dynamic UI schema (tabs, settings fields, badges, widgets) for the Host Shell."""
    return {"status": "success", "schema": plugin_manager.get_ui_schema()}


@app.get("/api/v3/extensions")
async def list_v3_extensions_endpoint():
    """Returns all extensions and their manifest declarations."""
    return {"status": "success", "extensions": plugin_manager.list_plugins()}


@app.post("/api/v3/extensions/{extension_id}/toggle")
async def toggle_v3_extension_endpoint(extension_id: str, data: dict):
    """Enable or disable an extension dynamically."""
    enabled = bool(data.get("enabled", True))
    success = plugin_manager.engine.set_extension_state(extension_id, enabled)
    if not success:
        raise HTTPException(status_code=404, detail=f"الإضافة '{extension_id}' غير موجودة")
    await log_message("ExtensionEngine", f"Extension '{extension_id}' toggled to: {enabled}")
    return {"status": "success", "extension_id": extension_id, "enabled": enabled}


@app.get("/api/v3/extensions/{extension_id}/settings")
async def get_v3_extension_settings_endpoint(extension_id: str):
    """Get isolated configuration for an extension."""
    ext = plugin_manager.engine.extensions.get(extension_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extension not found")
    return {"status": "success", "extension_id": extension_id, "config": ext.get_config()}


@app.post("/api/v3/extensions/{extension_id}/settings")
async def save_v3_extension_settings_endpoint(extension_id: str, data: dict):
    """Save isolated configuration for an extension."""
    ext = plugin_manager.engine.extensions.get(extension_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extension not found")
    success = ext.save_config(data)
    if success:
        await log_message("ExtensionEngine", f"Saved configuration for extension '{extension_id}'")
        return {"status": "success", "extension_id": extension_id, "config": ext.get_config()}
    raise HTTPException(status_code=500, detail="فشل حفظ إعدادات الإضافة")


# ---------------- Extension Studio & AI Workspace APIs ----------------

@app.get("/api/v3/extensions/{extension_id}/files")
async def get_extension_files(extension_id: str):
    """Lists all files in an extension directory for the workspace code editor."""
    ext = plugin_manager.engine.extensions.get(extension_id)
    if not ext:
        # Check if it's a legacy single file plugin
        legacy_file = Path(__file__).parent / "plugins" / f"{extension_id}.py"
        if legacy_file.exists():
            return {"status": "success", "extension_id": extension_id, "files": [f"{extension_id}.py"], "is_single_file": True}
        raise HTTPException(status_code=404, detail="Extension not found")

    file_list = []
    for p in ext.dir_path.rglob("*"):
        if p.is_file() and not any(part.startswith("__") or part.startswith(".") for part in p.parts) and not p.name.endswith(".pyc"):
            rel_path = str(p.relative_to(ext.dir_path))
            file_list.append(rel_path)

    # Sort files logically: manifest first, then backend, then ui files, then config
    def file_sort_key(name):
        if name == "manifest.json": return 0
        if name in ("backend.py", "adapter.py"): return 1
        if name.startswith("ui/"): return 2
        if name == "config.json": return 3
        return 4

    file_list.sort(key=file_sort_key)
    return {
        "status": "success",
        "extension_id": extension_id,
        "files": file_list,
        "is_single_file": False
    }


@app.get("/api/v3/extensions/{extension_id}/file")
async def get_extension_file_content(extension_id: str, path: str):
    """Retrieves file content for inspection in the workspace code viewer."""
    ext = plugin_manager.engine.extensions.get(extension_id)
    if not ext:
        # Check single file plugin
        legacy_file = Path(__file__).parent / "plugins" / f"{extension_id}.py"
        if legacy_file.exists() and path in (f"{extension_id}.py", ""):
            content = legacy_file.read_text(encoding="utf-8")
            return {"status": "success", "extension_id": extension_id, "path": f"{extension_id}.py", "content": content}
        raise HTTPException(status_code=404, detail="Extension not found")

    target_file = (ext.dir_path / path).resolve()
    # Security check: ensure path is inside extension directory
    if not str(target_file).startswith(str(ext.dir_path.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not target_file.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = target_file.read_text(encoding="utf-8")
        return {
            "status": "success",
            "extension_id": extension_id,
            "path": path,
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@app.post("/api/v3/extensions/{extension_id}/file")
async def save_extension_file_content(extension_id: str, data: dict):
    """Saves manual code edits directly into the extension's file."""
    path = data.get("path", "").strip()
    content = data.get("content", "")
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")

    ext = plugin_manager.engine.extensions.get(extension_id)
    if not ext:
        legacy_file = Path(__file__).parent / "plugins" / f"{extension_id}.py"
        if legacy_file.exists() and path == f"{extension_id}.py":
            legacy_file.write_text(content, encoding="utf-8")
            plugin_manager.load_plugins()
            return {"status": "success", "message": "تم حفظ كود الإضافة بنجاح!"}
        raise HTTPException(status_code=404, detail="Extension not found")

    target_file = (ext.dir_path / path).resolve()
    if not str(target_file).startswith(str(ext.dir_path.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content, encoding="utf-8")

        # Reload extension engine & mount routers if manifest or backend modified
        if path.endswith(".py") or path == "manifest.json":
            plugin_manager.load_plugins()
            plugin_manager.mount_extension_routers(app)

        await log_message("Workspace", f"Saved edits to '{extension_id}/{path}'")
        return {"status": "success", "message": f"تم حفظ الملف {path} بنجاح!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


@app.post("/api/v3/extensions/{extension_id}/ai-edit")
async def ai_edit_extension_file(extension_id: str, data: dict):
    """
    The AI Modification Box (Qwen 2.5 Coder):
    Takes user instruction in natural language and modifies the file in its exact place!
    """
    path = data.get("path", "").strip()
    instruction = data.get("instruction", "").strip()

    if not path or not instruction:
        raise HTTPException(status_code=400, detail="مسار الملف وتوجيهات التعديل مطلوبة")

    ext = plugin_manager.engine.extensions.get(extension_id)
    if not ext:
        legacy_file = Path(__file__).parent / "plugins" / f"{extension_id}.py"
        if legacy_file.exists() and path == f"{extension_id}.py":
            target_file = legacy_file
        else:
            raise HTTPException(status_code=404, detail="Extension not found")
    else:
        target_file = (ext.dir_path / path).resolve()
        if not str(target_file).startswith(str(ext.dir_path.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

    if not target_file.exists():
        raise HTTPException(status_code=404, detail="File does not exist")

    current_code = target_file.read_text(encoding="utf-8")
    config = load_config()

    # Balanced file-specific rules
    file_rules = ""
    if path.endswith(".py"):
        file_rules = """- ROLE: Lightweight backend logic for API communication, webhook processing, or event handling.
- RULES: Use standard libraries or `requests`. Do NOT build standalone servers (no Flask/Django). Keep FastAPI router or handle functions clean."""
    elif path.endswith(".html"):
        file_rules = """- ROLE: Dashboard UI tab component using Tailwind CSS.
- RULES: Output a clean <div> card with inputs, action buttons, and a status/result area. Do NOT wrap in <html> or <body> tags."""
    elif path.endswith(".json"):
        file_rules = """- ROLE: Configuration or manifest.
- RULES: Output 100% valid JSON with exact syntax."""

    system_msg = f"""
You are Qwen 2.5 Coder, a precision code editor for M.A.R.K.E.T v3 extensions.
You are editing the file `{path}` for extension `{extension_id}`.

[EXTENSION FILE ARCHITECTURE]:
{file_rules}

[CURRENT FILE CONTENT]:
```{path.split('.')[-1]}
{current_code}
```

[USER INSTRUCTION]:
{instruction}

[CRITICAL REQUIREMENTS]:
1. Return the COMPLETE, ready-to-run updated file content inside a single markdown code block (` ```...``` `).
2. Preserve all existing functionality unless explicitly asked to modify it.
3. Keep syntax 100% valid.
4. Do NOT output conversational chit-chat outside the code block.
"""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"نفّذ هذا التعديل على الملف بالكامل: {instruction}"}
    ]

    await log_message("QwenCoder", f"AI modifying '{extension_id}/{path}' with prompt: {instruction}")

    try:
        reply = await AIProviderManager.complete_coder(messages, config, temperature=0.1)
        if not reply:
            raise HTTPException(status_code=500, detail="تعذر الحصول على رد من محرك Qwen Coder")

        # Extract code from code block
        def extract_code_block(raw_text: str) -> str:
            clean = raw_text.strip()
            if "```" in clean:
                parts = clean.split("```")
                if len(parts) >= 2:
                    first_block = parts[1]
                    lines = first_block.split("\n", 1)
                    if len(lines) > 1 and lines[0].strip() in ("python", "json", "html", "js", "css"):
                        return lines[1].strip()
                    return first_block.strip()
            return clean

        new_code = extract_code_block(reply)

        # ── Automated Error Validation & Feedback Loop ────────────────────────
        validation_error = None
        if path.endswith(".py"):
            try:
                compile(new_code, path, "exec")
            except SyntaxError as syn_err:
                validation_error = f"SyntaxError on line {syn_err.lineno}: {syn_err.msg}"
        elif path.endswith(".json"):
            try:
                json.loads(new_code)
            except json.JSONDecodeError as json_err:
                validation_error = f"JSONDecodeError on line {json_err.lineno}: {json_err.msg}"

        if validation_error:
            await log_message("QwenCoder", f"[Feedback Loop]  Error detected in '{path}': {validation_error}. Sending feedback to omni_engine for repair...")
            repair_messages = [
                {
                    "role": "system",
                    "content": "You are an automated code fixer. Fix the exact syntax error and output ONLY the complete corrected file content inside a single markdown code block. No explanations."
                },
                {
                    "role": "user",
                    "content": f"The following code for `{path}` has an error:\n```{path.split('.')[-1]}\n{new_code}\n```\nError: {validation_error}\nPlease fix this error and output the complete valid code."
                }
            ]
            repaired_reply = await AIProviderManager.complete_coder(repair_messages, config, temperature=0.1)
            if repaired_reply:
                repaired_code = extract_code_block(repaired_reply)
                # Re-verify repaired code
                repair_passed = True
                if path.endswith(".py"):
                    try:
                        compile(repaired_code, path, "exec")
                    except Exception:
                        repair_passed = False
                elif path.endswith(".json"):
                    try:
                        json.loads(repaired_code)
                    except Exception:
                        repair_passed = False

                if repair_passed:
                    new_code = repaired_code
                    await log_message("QwenCoder", f"[Feedback Loop]  omni_engine successfully auto-repaired '{path}'!")
                else:
                    await log_message("QwenCoder", f"[Feedback Loop]  Auto-repair attempted, saving best version.")

        # Save the updated content directly to the file!
        target_file.write_text(new_code, encoding="utf-8")

        # Auto-reload extensions and routes
        plugin_manager.load_plugins()
        plugin_manager.mount_extension_routers(app)

        await log_message("QwenCoder", f"Successfully updated and saved '{extension_id}/{path}'")

        return {
            "status": "success",
            "extension_id": extension_id,
            "path": path,
            "new_content": new_code,
            "message": f"تم تطبيق التعديل وحفظه تلقائياً في {path} وتحديث السيرفر بنجاح! "
        }
    except Exception as e:
        logger.error(f"AI Edit error: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في تعديل الملف عبر الذكاء الاصطناعي: {str(e)}")


# ---------------------------------------------------------------------------
# Scratch Visual Block Flow Engine Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/v3/scratch/blocks")
async def get_scratch_blocks():
    """Returns dynamically discovered Scratch blocks (core + installed plugins)."""
    import scratch_engine
    blocks = scratch_engine.discover_dynamic_blocks()
    return {"status": "success", "blocks": blocks}

@app.get("/api/v3/scratch/flow")
async def get_scratch_flow(extension_id: str = "whatsapp_openwa"):
    """Returns the saved or default Scratch block flow for an extension."""
    import scratch_engine
    ext = plugin_manager.engine.extensions.get(extension_id)
    if ext:
        flow_file = ext.dir_path / "flow.json"
        if flow_file.exists():
            try:
                flow = json.loads(flow_file.read_text(encoding="utf-8"))
                return {"status": "success", "extension_id": extension_id, "flow": flow, "is_saved": True}
            except Exception:
                pass
    default_flow = scratch_engine.get_default_flow_for_extension(extension_id)
    return {"status": "success", "extension_id": extension_id, "flow": default_flow, "is_saved": False}

@app.post("/api/v3/scratch/save-flow")
async def save_scratch_flow(request: Request):
    """Saves block flow to plugins/<extension_id>/flow.json."""
    data = await request.json()
    extension_id = data.get("extension_id", "").strip() or "whatsapp_openwa"
    flow = data.get("flow", [])
    edges = data.get("edges", [])
    if not extension_id:
        raise HTTPException(status_code=400, detail="معرف الإضافة مطلوب")

    plugins_dir = Path(__file__).parent / "plugins"
    ext_dir = plugins_dir / extension_id
    ext_dir.mkdir(parents=True, exist_ok=True)

    manifest_file = ext_dir / "manifest.json"
    if not manifest_file.exists():
        manifest_data = {
            "manifest_version": 3,
            "id": extension_id,
            "name": data.get("name", extension_id.replace("_", " ").title()),
            "version": "1.0.0",
            "description": data.get("description", "إضافة مخصصة تم تصميمها عبر استوديو سكراتش الموجه بالذكاء الاصطناعي"),
            "author": "M.A.R.K.E.T Scratch Studio",
            "icon": "sparkles",
            "entrypoint": "backend.py",
            "permissions": ["network", "ai", "webhooks"],
            "enabled": True,
            "routes": {
                "prefix": f"/ext/{extension_id}",
                "webhooks": ["/webhook", "/execute"]
            }
        }
        manifest_file.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")

    nodes = flow.get("nodes", flow) if isinstance(flow, dict) else flow
    flow_to_save = {
        "nodes": nodes,
        "edges": edges if edges else (flow.get("edges", []) if isinstance(flow, dict) else [])
    }
    flow_file = ext_dir / "flow.json"
    flow_file.write_text(json.dumps(flow_to_save, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Reload plugins
    plugin_manager.load_plugins()
    plugin_manager.mount_extension_routers(app)
    await log_message("ScratchEngine", f"تم حفظ مخطط المكعبات وتحديث الإضافة '{extension_id}' بنجاح في {flow_file}")
    
    return {
        "status": "success",
        "extension_id": extension_id,
        "path": str(flow_file),
        "message": f"تم حفظ مخطط المكعبات بنجاح في {extension_id}/flow.json"
    }

@app.post("/api/v3/scratch/compile")
async def compile_scratch_flow(request: Request):
    """Compiles visual blocks into Python code and writes to backend.py."""
    import scratch_engine
    data = await request.json()
    extension_id = data.get("extension_id", "").strip() or "whatsapp_openwa"
    flow = data.get("flow", [])
    edges = data.get("edges", [])
    save_to_backend = data.get("save_to_backend", True)
    if not extension_id:
        raise HTTPException(status_code=400, detail="معرف الإضافة مطلوب")

    nodes = flow.get("nodes", flow) if isinstance(flow, dict) else flow
    compiled_code = scratch_engine.compile_flow_to_python(nodes, extension_id)
    
    plugins_dir = Path(__file__).parent / "plugins"
    ext_dir = plugins_dir / extension_id
    ext_dir.mkdir(parents=True, exist_ok=True)

    manifest_file = ext_dir / "manifest.json"
    if not manifest_file.exists():
        manifest_data = {
            "manifest_version": 3,
            "id": extension_id,
            "name": data.get("name", extension_id.replace("_", " ").title()),
            "version": "1.0.0",
            "description": data.get("description", "إضافة مخصصة تم تصميمها وترجمتها عبر Qwen 2.5 Coder"),
            "author": "M.A.R.K.E.T Scratch Studio",
            "icon": "code",
            "entrypoint": "backend.py",
            "permissions": ["network", "ai", "webhooks"],
            "enabled": True,
            "routes": {
                "prefix": f"/ext/{extension_id}",
                "webhooks": ["/webhook", "/execute"]
            }
        }
        manifest_file.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")

    flow_to_save = {
        "nodes": nodes,
        "edges": edges if edges else (flow.get("edges", []) if isinstance(flow, dict) else [])
    }
    flow_file = ext_dir / "flow.json"
    flow_file.write_text(json.dumps(flow_to_save, ensure_ascii=False, indent=2), encoding="utf-8")

    backend_file = ext_dir / "backend.py"
    if save_to_backend:
        backend_file.write_text(compiled_code, encoding="utf-8")
        plugin_manager.load_plugins()
        plugin_manager.mount_extension_routers(app)
        await log_message("ScratchEngine", f" تم ترجمة وتفعيل {extension_id}/backend.py و flow.json وحفظها في المجلد بنجاح.")

    return {
        "status": "success",
        "extension_id": extension_id,
        "backend_file": str(backend_file),
        "flow_file": str(flow_file),
        "code": compiled_code,
        "message": f"تم ترجمة المكعبات إلى بايثون وحفظها وتفعيلها في plugins/{extension_id}/backend.py بنجاح! "
    }


@app.post("/api/v3/scratch/synthesize-node")
async def synthesize_scratch_node(request: Request):
    """
    Calls Qwen 2.5 Coder (via AIProviderManager) to synthesize a fully-formed interactive Scratch Node
    including UI fields, input/output sockets, and Python DAG logic.
    """
    data = await request.json()
    user_prompt = data.get("prompt", "").strip()
    category = data.get("category", "data")
    custom_title = data.get("title", "").strip()
    branching_type = data.get("branching_type", "single") # single, dual, parallel

    if not user_prompt:
        raise HTTPException(status_code=400, detail="وصف العقدة أو متطلبات المنطق مطلوبة")

    config = load_config()

    system_instruction = """You are Qwen 2.5 Coder, the AI Node Architect for M.A.R.K.E.T Studio.
Transform the user's natural language requirements into a valid, production-ready interactive visual node schema for our drag-and-drop studio.

Output MUST be a single, strictly valid JSON object (no markdown quotes, no explanations outside JSON) following this exact schema:
{
  "id": "custom_<slug>_<timestamp>",
  "name": "عنوان العقدة بالعربية المهنية الواضحة",
  "description": "شرح وظيفي مختصر وواضح لما تقوم به العقدة",
  "category": "triggers" | "data" | "ai" | "routing" | "offers" | "dispatch" | "custom",
  "color": "#HEX_COLOR",
  "icon": "Lucide icon name (e.g. Tag, FileSpreadsheet, Code, Database, Filter, Sparkles, Sliders, ShieldCheck, Send, Cpu, Layers)",
  "fields": [
    {
      "key": "machine_field_key",
      "label": "اسم الحقل بالعربية للمستخدم",
      "type": "text" | "code" | "textarea" | "select" | "toggle" | "file" | "number",
      "default": "القيمة الافتراضية المناسبة",
      "placeholder": "نص إرشادي اختياري داخل الحقل",
      "options": ["خيار 1", "خيار 2"]
    }
  ],
  "inputs": [
    { "id": "in", "label": "دخول التدفق" }
  ],
  "outputs": [
    { "id": "out_1", "label": "اسم المخرج بالعربية", "color": "#HEX" }
  ],
  "python_logic": "Executable Python code snippet representing this step in the DAG. Has access to context (dict), fields (dict), and execution_log (list).",
  "simulation_logic": {
    "type": "match",
    "target_field": "machine_field_key",
    "match_mode": "exact"
  }
}
"""

    user_req = f"""[USER REQUIREMENTS]:
- Description / Goal: {user_prompt}
- Preferred Category: {category}
- Custom Title (if provided): {custom_title or 'Generate appropriate title'}
- Branching Preference: {branching_type} (single = 1 output, dual = 2 outputs like true/false or match/nomatch, parallel = broadcast)

Synthesize the complete interactive node definition JSON now:"""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_req}
    ]

    raw_response = None
    try:
        raw_response = await AIProviderManager.complete_chat(messages, config, temperature=0.2)
    except Exception as e:
        logger.warning(f"complete_chat failed during node synthesis: {e}")

    node_schema = None
    if raw_response:
        cleaned = raw_response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        try:
            node_schema = json.loads(cleaned)
        except Exception as e:
            logger.warning(f"JSON parsing error from Qwen response: {e}")

    # If LLM didn't return valid JSON, synthesize a safe, structured fallback schema based on user inputs
    if not node_schema or not isinstance(node_schema, dict) or "fields" not in node_schema:
        import time
        slug = "".join(c for c in (custom_title or "custom_node").lower() if c.isalnum() or c == "_")[:20] or "custom_node"
        node_id = f"custom_{slug}_{int(time.time())}"
        
        if branching_type == "dual":
            outputs = [
                {"id": "out_primary", "label": "المسار الأساسي (متطابق / فعال)", "color": "#10B981"},
                {"id": "out_secondary", "label": "المسار البديل (غير متطابق / منتهي)", "color": "#EF4444"}
            ]
        elif branching_type == "parallel":
            outputs = [
                {"id": "out_fork_1", "label": "تفرع موازي 1", "color": "#3B82F6"},
                {"id": "out_fork_2", "label": "تفرع موازي 2", "color": "#8B5CF6"}
            ]
        else:
            outputs = [
                {"id": "out", "label": "المسار التالي", "color": "#3B82F6"}
            ]

        fields = []
        is_excel_or_file = any(w in user_prompt.lower() for w in ("excel", "اكسيل", "إكسيل", "ملف", "شيت", "sheet", "csv"))
        is_code_or_promo = any(w in user_prompt.lower() for w in ("كود", "رمز", "promo", "code", "تطابق", "خصم"))

        if is_excel_or_file:
            fields.append({
                "key": "file_path",
                "label": "مسار ملف الإكسيل (Excel / CSV Path)",
                "type": "file",
                "default": "data/inventory.xlsx",
                "placeholder": "data/inventory.xlsx أو اضغط لرفع ملف"
            })
            fields.append({
                "key": "sheet_name",
                "label": "اسم الشيت (Sheet Name)",
                "type": "text",
                "default": "Sheet1",
                "placeholder": "Sheet1"
            })
            fields.append({
                "key": "target_column",
                "label": "عمود البحث والمطابقة",
                "type": "text",
                "default": "code",
                "placeholder": "code, price, stock"
            })
        elif is_code_or_promo:
            fields.append({
                "key": "target_codes",
                "label": "أكواد الخصم / الرموز المعتمدة",
                "type": "code",
                "default": "SAVE10, VIP2026, SUMMER50",
                "placeholder": "أدخل الأكواد مفصولة بفواصل (مثل: SAVE20, VIP50)"
            })
            fields.append({
                "key": "match_mode",
                "label": "نوع الفحص والمطابقة",
                "type": "select",
                "options": ["تطابق تام بنسبة 100%", "بحث جزئي يحتوي على الكلمة", "حساس للأحرف (Case-Sensitive)"],
                "default": "تطابق تام بنسبة 100%"
            })
        else:
            fields.append({
                "key": "parameter_value",
                "label": "القيمة أو النص المخصص",
                "type": "text",
                "default": "",
                "placeholder": "أدخل القيمة المراد تمريرها للعقدة"
            })

        node_schema = {
            "id": node_id,
            "name": custom_title or ("فاحص أكواد ومطابقة" if is_code_or_promo else ("قارئ ملفات Excel" if is_excel_or_file else "عقدة مخصصة")),
            "description": user_prompt[:120],
            "category": category,
            "color": "#3B82F6" if category == "data" else ("#10B981" if category == "offers" else "#8B5CF6"),
            "icon": "FileSpreadsheet" if is_excel_or_file else ("Tag" if is_code_or_promo else "Code"),
            "fields": fields,
            "inputs": [] if category == "triggers" else [{"id": "in", "label": "دخول التدفق"}],
            "outputs": outputs,
            "python_logic": f"# Custom execution logic for: {user_prompt}\nexecution_log.append(f'Executed {node_id}')",
            "simulation_logic": {"type": "match" if is_code_or_promo else "default"}
        }

    # Save to custom_blocks.json so it's persisted in the palette library
    plugins_dir = Path(__file__).parent / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    custom_blocks_file = plugins_dir / "custom_blocks.json"
    
    existing_blocks = []
    if custom_blocks_file.exists():
        try:
            existing_blocks = json.loads(custom_blocks_file.read_text(encoding="utf-8"))
        except Exception:
            existing_blocks = []
    
    existing_blocks = [b for b in existing_blocks if b.get("id") != node_schema.get("id")]
    existing_blocks.append(node_schema)
    custom_blocks_file.write_text(json.dumps(existing_blocks, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "node": node_schema,
        "message": f"تم توليد وهندسة العقدة '{node_schema.get('name')}' بالذكاء الاصطناعي بنجاح! ✨"
    }


@app.get("/api/v3/scratch/custom-blocks")
async def get_custom_scratch_blocks():
    """Returns all custom AI generated blocks saved in plugins/custom_blocks.json."""
    plugins_dir = Path(__file__).parent / "plugins"
    custom_blocks_file = plugins_dir / "custom_blocks.json"
    if custom_blocks_file.exists():
        try:
            blocks = json.loads(custom_blocks_file.read_text(encoding="utf-8"))
            return {"status": "success", "blocks": blocks}
        except Exception as e:
            return {"status": "error", "message": str(e), "blocks": []}
    return {"status": "success", "blocks": []}


@app.delete("/api/v3/scratch/custom-blocks/{block_id}")
async def delete_custom_scratch_block(block_id: str):
    """Deletes a custom AI generated block from plugins/custom_blocks.json."""
    plugins_dir = Path(__file__).parent / "plugins"
    custom_blocks_file = plugins_dir / "custom_blocks.json"
    if custom_blocks_file.exists():
        try:
            blocks = json.loads(custom_blocks_file.read_text(encoding="utf-8"))
            blocks = [b for b in blocks if b.get("id") != block_id]
            custom_blocks_file.write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"status": "success", "message": f"تم حذف العقدة {block_id} بنجاح"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success", "message": "لم يتم العثور على ملف العقد المخصصة"}


@app.post("/api/v3/scratch/generate-ai-pipeline")
async def generate_scratch_ai_pipeline(request: Request):
    """
    Takes the 4 generalized steps + user custom notes and prompts Qwen 2.5 Coder
    to write the complete, tailored backend.py file for the extension.
    """
    import scratch_engine
    data = await request.json()
    extension_id = data.get("extension_id", "whatsapp_openwa").strip()
    pipeline_data = data.get("pipeline", {})
    save_to_backend = data.get("save_to_backend", True)

    if not extension_id:
        raise HTTPException(status_code=400, detail="معرف الإضافة مطلوب")

    await log_message("ScratchAI", f"Qwen 2.5 Coder synthesizing custom pipeline for '{extension_id}'...")
    
    config = load_config()
    blocks_list = data.get("blocks")
    pipeline_data = data.get("pipeline", {})

    if blocks_list and isinstance(blocks_list, list):
        # Format free-form Scratch blocks sequence
        blocks_spec = []
        for idx, b in enumerate(blocks_list, 1):
            b_cat = b.get("category", "action")
            b_name = b.get("name", b.get("title", b_cat))
            b_notes = b.get("notes", b.get("description", ""))
            b_val = b.get("values", {})
            if b_cat == "custom_fn" or b.get("id") == "custom_fn":
                fn_name = b_val.get("fn_name", f"custom_function_{idx}")
                blocks_spec.append(f"{idx}. [CUSTOM FUNCTION - {fn_name}]: User specification: '{b_notes}'. You MUST write a dedicated Python function for this logic and execute it in this step.")
            else:
                blocks_spec.append(f"{idx}. [{b_cat.upper()} - {b_name}]: Parameters: {json.dumps(b_val, ensure_ascii=False)} | Intent & Instructions: '{b_notes}'")

        blocks_summary = "\n".join(blocks_spec)
        prompt = f"""You are Qwen 2.5 Coder, an expert Python backend engineer for M.A.R.K.E.T v3.
Your task is to write the complete, clean, executable Python file `backend.py` for extension `{extension_id}`.

[SCRATCH VISUAL BLOCKS PIPELINE (EXECUTE IN THIS EXACT SEQUENCE)]:
{blocks_summary}

[CRITICAL INSTRUCTIONS]:
1. For any [CUSTOM FUNCTION] step, declare and implement the Python helper function cleanly above the router endpoints.
2. Maintain strict grounding with SQLite `market.db` for database steps (zero hallucination).
3. Connect all steps sequentially in the async endpoint handler.
4. Output ONLY valid, executable Python code inside a single ```python ``` code block.
"""
    else:
        # 4-step pipeline fallback
        trigger_step = pipeline_data.get("trigger", {})
        data_step = pipeline_data.get("data", {})
        ai_step = pipeline_data.get("ai", {})
        dispatch_step = pipeline_data.get("dispatch", {})

        prompt = f"""You are Qwen 2.5 Coder, an expert Python backend engineer for M.A.R.K.E.T v3.
Your task is to write the complete, clean, executable Python file `backend.py` for extension `{extension_id}`.

[PIPELINE ARCHITECTURE SPECIFICATION]:
1. INGEST / TRIGGER:
   - Source Channel: {trigger_step.get('channel', 'whatsapp')}
   - User Intent & Trigger Rules: {trigger_step.get('notes', 'Receive incoming message')}

2. DATA GROUNDING / SQL (Zero Hallucination):
   - Data Source: {data_step.get('source', 'SQL database (market.db)')}
   - Required Data & Rules: {data_step.get('notes', 'Query product prices and stock')}

3. AI REASONING / OMNI CORE:
   - AI Role / Task: {ai_step.get('role', 'Customer Care & Sales')}
   - User Custom Prompt & Rules: {ai_step.get('notes', 'Polite Egyptian Arabic, strictly follow SQL facts')}

4. DISPATCH / OUTPUT ACTION:
   - Destination: {dispatch_step.get('destination', 'Reply via same channel')}
   - Action Details: {dispatch_step.get('notes', 'Send message back to user')}

[TECHNICAL REQUIREMENTS]:
- Output ONLY valid, executable Python code inside a ```python ``` block.
- Create an APIRouter with prefix `/ext/{extension_id}` and tags [`{extension_id}`].
- Provide an endpoint `/webhook` or `/execute` or appropriate route matching the source channel.
- Implement strict database queries to SQLite `market.db` (zero hallucination).
- Handle exceptions cleanly and return standard JSON response.
- Do NOT truncate code, write full implementations.
"""

    messages = [
        {"role": "system", "content": "You are Qwen 2.5 Coder. Write production-ready, clean Python code adhering strictly to the user's pipeline architecture without any fluff."},
        {"role": "user", "content": prompt}
    ]

    try:
        raw_code = await AIProviderManager.complete_coder(messages, config, temperature=0.1)
    except Exception as e:
        logger.warning(f"complete_coder failed: {e}")
        raw_code = None

    if not raw_code:
        # Fallback to robust scratch_engine flow compiler
        default_flow = scratch_engine.get_default_flow_for_extension(extension_id)
        raw_code = scratch_engine.compile_flow_to_python(default_flow, extension_id)

    generated_code = raw_code.strip()
    if "```python" in generated_code:
        generated_code = generated_code.split("```python", 1)[1].split("```", 1)[0].strip()
    elif "```" in generated_code:
        generated_code = generated_code.split("```", 1)[1].split("```", 1)[0].strip()

    if save_to_backend:
        plugins_dir = Path(__file__).parent / "plugins"
        ext_dir = plugins_dir / extension_id
        ext_dir.mkdir(parents=True, exist_ok=True)

        manifest_file = ext_dir / "manifest.json"
        if not manifest_file.exists():
            manifest_data = {
                "manifest_version": 3,
                "id": extension_id,
                "name": extension_id.replace("_", " ").title(),
                "version": "1.0.0",
                "description": "إضافة مخصصة تم توليدها بواسطة Qwen 2.5 Coder",
                "author": "M.A.R.K.E.T AI",
                "icon": "sparkles",
                "entrypoint": "backend.py",
                "permissions": ["network", "ai", "webhooks"],
                "enabled": True,
                "routes": {
                    "prefix": f"/ext/{extension_id}",
                    "webhooks": ["/webhook", "/execute"]
                }
            }
            manifest_file.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")

        backend_file = ext_dir / "backend.py"
        backend_file.write_text(generated_code, encoding="utf-8")
        pipeline_file = ext_dir / "pipeline.json"
        pipeline_file.write_text(json.dumps(pipeline_data, ensure_ascii=False, indent=2), encoding="utf-8")
        plugin_manager.load_plugins()
        plugin_manager.mount_extension_routers(app)
        await log_message("ScratchAI", f"Successfully compiled and deployed '{extension_id}/backend.py' via Qwen 2.5 Coder!")

    return {
        "status": "success",
        "extension_id": extension_id,
        "backend_file": str(plugins_dir / extension_id / "backend.py"),
        "code": generated_code,
        "message": f"تم توليد كود بايثون وحفظه وتفعيله بنجاح في plugins/{extension_id}/backend.py عبر Qwen 2.5 Coder! "
    }


@app.get("/api/v3/engine/models-status")
async def get_models_status():
    """
    Confirms Multi-Model Concurrency:
    - Model 1: Qwen 2.5 Coder 0.5B (Dedicated to Extension Studio & coding)
    - Model 2: Customer Care & Chat Model (Gemini / Groq / Ollama / Llama)
    """
    config = load_config()
    chat_provider = config.get("ai_provider", "custom")
    chat_model = config.get(f"{chat_provider}_model", "unknown")
    coder_model = config.get("coder_model", "qwen2.5-coder:0.5b")

    return {
        "status": "success",
        "multi_model_concurrency_enabled": True,
        "models": {
            "coder": {
                "name": coder_model,
                "role": "مبرمج الإضافات والاستوديو (Extension Coder & AI Box)",
                "isolated": True
            },
            "customer_service": {
                "provider": chat_provider,
                "name": chat_model,
                "role": "خدمة العملاء والرد على المحادثات وقنوات التواصل (Customer Care & Channels)",
                "isolated": True
            }
        },
        "description": "المحرك يدعم تشغيل الموديلين في نفس الوقت بدون أي تعارض؛ كل طلب يوجه لموديله المخصص."
    }


# ---------------- Developer Debug & Inspector Suite APIs ----------------

@app.post("/api/v3/debug/sql-query")
async def debug_sql_query(request: Request):
    """
    Executes an SQL query against the SQLite WAL database (market_edge.db) for real-time debugging.
    Returns result rows, column headers, execution time, and DB statistics.
    """
    from database import db, DB_PATH
    data = await request.json()
    query = data.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="SQL query cannot be empty")

    db_path = DB_PATH
    wal_path = db_path.parent / f"{db_path.name}-wal"
    shm_path = db_path.parent / f"{db_path.name}-shm"

    start_time = time.perf_counter()
    columns = []
    rows = []
    error = None
    rowcount = 0

    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(query)
        
        if cur.description:
            columns = [d[0] for d in cur.description]
            fetched = cur.fetchmany(100)
            rows = [dict(r) for r in fetched]
            rowcount = len(rows)
        else:
            conn.commit()
            rowcount = cur.rowcount
            columns = ["affected_rows"]
            rows = [{"affected_rows": rowcount}]
            
        conn.close()
    except Exception as e:
        error = str(e)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    db_size = db_path.stat().st_size if db_path.exists() else 0
    wal_size = wal_path.stat().st_size if wal_path.exists() else 0
    shm_size = shm_path.stat().st_size if shm_path.exists() else 0

    return {
        "status": "success" if error is None else "error",
        "query": query,
        "execution_time_ms": elapsed_ms,
        "row_count": rowcount,
        "columns": columns,
        "rows": rows,
        "error": error,
        "db_stats": {
            "db_size_bytes": db_size,
            "wal_size_bytes": wal_size,
            "shm_size_bytes": shm_size,
            "journal_mode": "wal"
        }
    }


@app.post("/api/v3/debug/llm-benchmark")
async def debug_llm_benchmark(request: Request):
    """
    Directly benchmarks the active AI Provider or Qwen 2.5 Coder.
    Measures latency, token estimation, and raw output.
    """
    data = await request.json()
    prompt = data.get("prompt", "Hello test").strip()
    target_role = data.get("role", "chat") # 'chat' or 'coder'
    system_prompt = data.get("system_prompt", "You are an AI benchmark tester.")
    
    config = load_config()
    start_time = time.perf_counter()
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    response_text = ""
    error = None
    try:
        if target_role == "coder":
            response_text = await AIProviderManager.complete_coder(messages, config, temperature=0.1)
        else:
            response_text = await AIProviderManager.complete(messages, config, temperature=0.3)
    except Exception as e:
        error = str(e)
        
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    # Approximate tokens
    prompt_tokens = len(prompt.split()) + len(system_prompt.split())
    completion_tokens = len((response_text or "").split())
    
    return {
        "status": "success" if error is None else "error",
        "target_role": target_role,
        "provider": config.get("ai_provider", "custom") if target_role != "coder" else "local_coder",
        "model": config.get("coder_model", "qwen2.5-coder:0.5b") if target_role == "coder" else config.get(f"{config.get('ai_provider', 'custom')}_model", "default"),
        "latency_ms": elapsed_ms,
        "prompt_tokens_est": prompt_tokens,
        "completion_tokens_est": completion_tokens,
        "tokens_per_sec": round(completion_tokens / (elapsed_ms / 1000 + 0.001), 2) if completion_tokens else 0,
        "response": response_text,
        "error": error
    }


@app.get("/api/v3/debug/system-metrics")
async def debug_system_metrics():
    """
    Comprehensive live telemetry metrics for Developer Debugger Suite.
    """
    import psutil
    hw = get_system_hardware()
    config = load_config()
    
    db_path = Path(__file__).parent / "market.db"
    wal_path = Path(__file__).parent / "market.db-wal"
    custom_blocks_file = Path(__file__).parent / "plugins" / "custom_blocks.json"
    
    custom_blocks_count = 0
    if custom_blocks_file.exists():
        try:
            custom_blocks_count = len(json.loads(custom_blocks_file.read_text(encoding="utf-8")))
        except Exception:
            pass
            
    uptime_sec = round(time.time() - SERVER_START_TIME, 1)
    
    return {
        "status": "success",
        "uptime_seconds": uptime_sec,
        "hardware": hw,
        "database": {
            "db_size_kb": round((db_path.stat().st_size if db_path.exists() else 0) / 1024, 2),
            "wal_size_kb": round((wal_path.stat().st_size if wal_path.exists() else 0) / 1024, 2),
            "engine": "SQLite WAL"
        },
        "extensions": {
            "custom_blocks_count": custom_blocks_count,
            "installed_plugins": plugin_manager.list_plugins() if hasattr(plugin_manager, "list_plugins") else []
        },
        "ai_models": {
            "active_chat_provider": config.get("ai_provider", "custom"),
            "active_chat_model": config.get(f"{config.get('ai_provider', 'custom')}_model", "unknown"),
            "coder_model": config.get("coder_model", "qwen2.5-coder:0.5b")
        }
    }



# ---------------- WhatsApp (OpenWA Gateway) APIs ----------------

def get_whatsapp_adapter_instance():
    """Returns or lazily creates the WhatsApp OpenWA adapter instance with current config."""
    global _whatsapp_adapter
    config = load_config()
    openwa_url = config.get("whatsapp_openwa_url", "http://localhost:2785")
    api_key = config.get("whatsapp_openwa_api_key", "")
    session_id = config.get("whatsapp_session_id", "market-bot")

    if _whatsapp_adapter is None:
        from plugins.whatsapp_openwa.adapter import WhatsAppAdapter
        _whatsapp_adapter = WhatsAppAdapter(
            openwa_url=openwa_url,
            api_key=api_key,
            session_id=session_id,
        )
    else:
        _whatsapp_adapter.client.base_url = openwa_url.rstrip("/")
        _whatsapp_adapter.client.api_key = api_key
        _whatsapp_adapter.session_id = session_id
    return _whatsapp_adapter


@app.get("/api/whatsapp/status")
async def get_whatsapp_status_endpoint():
    """Checks and returns the current WhatsApp session status from OpenWA."""
    try:
        adapter = get_whatsapp_adapter_instance()
        status = await adapter.get_status()
        return status
    except Exception as e:
        logger.error(f"WhatsApp status check error: {e}")
        return {
            "status": "error",
            "connection_status": "error",
            "is_connected": False,
            "has_qr": False,
            "error": str(e),
            "platform": "whatsapp"
        }


@app.post("/api/whatsapp/connect")
async def connect_whatsapp_endpoint():
    """Initiates WhatsApp session connection and requests QR code if needed."""
    try:
        adapter = get_whatsapp_adapter_instance()
        await log_message("WhatsApp", f"Connecting session '{adapter.session_id}' via OpenWA...")
        result = await adapter.connect()
        await log_message("WhatsApp", f"Connection result: status={result.get('connection_status')}")
        return result
    except Exception as e:
        logger.error(f"WhatsApp connection error: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في الاتصال بالواتساب: {str(e)}")


@app.post("/api/whatsapp/disconnect")
async def disconnect_whatsapp_endpoint():
    """Disconnects the active WhatsApp session."""
    try:
        adapter = get_whatsapp_adapter_instance()
        await log_message("WhatsApp", f"Disconnecting session '{adapter.session_id}'...")
        result = await adapter.disconnect()
        return result
    except Exception as e:
        logger.error(f"WhatsApp disconnect error: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في قطع اتصال الواتساب: {str(e)}")


@app.get("/api/whatsapp/qr")
async def get_whatsapp_qr_endpoint():
    """Retrieves the active QR code for WhatsApp web pairing."""
    try:
        adapter = get_whatsapp_adapter_instance()
        qr_result = await adapter.get_qr()
        return qr_result
    except Exception as e:
        logger.error(f"WhatsApp QR retrieval error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/whatsapp/pair-mock")
async def pair_mock_whatsapp_endpoint(data: Optional[dict] = None):
    """Simulates instant smartphone QR scan & pairing for testing."""
    try:
        adapter = get_whatsapp_adapter_instance()
        phone = (data or {}).get("phone", "+201012345678")
        result = await adapter.pair_session(phone)
        await log_message("WhatsApp", f"Device paired successfully (phone: {phone})")
        return result
    except Exception as e:
        logger.error(f"WhatsApp mock pairing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/whatsapp/send")
async def send_whatsapp_message_endpoint(data: dict):
    """Sends an outbound WhatsApp text or media message."""
    phone = data.get("phone", data.get("chat_id", "")).strip()
    text = data.get("message", data.get("text", "")).strip()
    image_url = data.get("image_url", "").strip() or None

    if not phone:
        raise HTTPException(status_code=400, detail="رقم الهاتف أو معرف المحادثة مطلوب")
    if not text and not image_url:
        raise HTTPException(status_code=400, detail="نص الرسالة أو رابط الصورة مطلوب")

    try:
        adapter = get_whatsapp_adapter_instance()
        result = await adapter.send_message(phone, text, image_url=image_url)
        if result.get("status") == "success":
            await log_message("WhatsApp", f"Outbound message sent to {phone}")
            return result
        raise HTTPException(status_code=400, detail=result.get("message", "فشل إرسال الرسالة"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في إرسال الرسالة: {str(e)}")


@app.post("/api/whatsapp/register-webhook")
async def register_whatsapp_webhook_endpoint(data: Optional[dict] = None):
    """Registers the M.A.R.K.E.T webhook URL with OpenWA gateway for automatic incoming message delivery."""
    try:
        adapter = get_whatsapp_adapter_instance()
        default_url = f"{WEBHOOK_URL.replace('/webhook', '')}/api/whatsapp/webhook" if WEBHOOK_URL else f"http://{get_local_ip()}:{settings.port}/api/whatsapp/webhook"
        target_url = (data or {}).get("webhook_url", default_url)
        res = await adapter.register_webhook(target_url)
        await log_message("WhatsApp", f"Registered OpenWA webhook target: {target_url} -> {res.get('status')}")
        return res
    except Exception as e:
        logger.error(f"WhatsApp register webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في تسجيل Webhook: {str(e)}")


@app.post("/api/whatsapp/webhook")
async def receive_whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives incoming event/message webhooks from OpenWA Gateway."""
    try:
        raw_body = await request.body()
        payload = json.loads(raw_body.decode("utf-8"))

        adapter = get_whatsapp_adapter_instance()
        msg = adapter.parse_webhook_event(payload)

        if msg:
            background_tasks.add_task(
                process_whatsapp_message_background,
                msg.chat_id,
                msg.text,
                msg.media_url,
                msg.message_id
            )
            return {"status": "success", "event": "message_queued"}

        return {"status": "success", "event": payload.get("event", "status_processed")}
    except Exception as e:
        logger.error(f"WhatsApp webhook processing error: {e}")
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(e)})


async def process_whatsapp_message_background(
    sender_id: str,
    message_text: str,
    image_url: Optional[str],
    message_id: Optional[str]
):
    """Background worker for incoming WhatsApp messages with full AI reply & plugin execution."""
    try:
        user_input = message_text or "[صورة / وسائط واتساب]"
        await log_message("WhatsApp", f"Incoming WhatsApp msg from {sender_id}: {user_input}")

        reply = await process_incoming_message(
            sender_id=sender_id,
            message_text=message_text,
            image_url=image_url,
            message_id=message_id,
            channel="whatsapp"
        )
        if reply:
            await log_message("Bot", f"Replied to WhatsApp {sender_id}: {reply[:90]}...")
    except Exception as e:
        await log_message("Error", f"WhatsApp message background processing error: {e}")


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


# ---------------- Atomic Checkout & ACID Storage API ----------------

@app.post("/api/checkout")
async def process_checkout_endpoint(data: dict):
    """
    ACID-compliant atomic checkout.
    Uses SQLite WAL mode atomic decrement to eliminate race conditions under concurrent orders.
    """
    product_code = data.get("product_code", "")
    quantity = int(data.get("quantity", 1))
    phone = data.get("customer_phone", "")
    name = data.get("customer_name", "عميل المتجر")
    channel = data.get("channel", "web")

    if not product_code or not phone:
        raise HTTPException(status_code=400, detail="كود المنتج ورقم الهاتف مطلوبان لإتمام الطلب")

    from database import db
    res = db.atomic_checkout(product_code, quantity, phone, name, channel)
    if res.get("success"):
        # Auto-sync back to Excel sheet to keep both updated
        db.sync_to_excel()
        excel_cache.reload()
        await log_message("Checkout", f"Atomic order confirmed: {name} ({product_code} x{quantity}) - Total: {res.get('total_price')} EGP")
        return {"status": "success", "order": res}

    raise HTTPException(status_code=400, detail=res.get("error", "تعذر إتمام عملية الشراء"))


@app.get("/api/database/status")
async def get_database_status():
    """Returns real-time health and telemetry of the SQLite WAL storage engine."""
    from database import db
    products = db.get_all_products()
    return {
        "status": "healthy",
        "engine": "SQLite (WAL Mode)",
        "journal_mode": "WAL",
        "concurrency": "ACID Multi-Reader / Single-Writer",
        "total_products": len(products),
        "db_file": str(db.db_path)
    }


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


def verify_meta_hmac_signature(raw_body: bytes, signature_header: Optional[str], app_secret: str) -> bool:
    """Verifies X-Hub-Signature-256 for Meta Webhook security to prevent spoofing/DoS."""
    if not app_secret or not signature_header:
        return True
    try:
        if not signature_header.startswith("sha256="):
            return False
        expected_sig = signature_header.split("sha256=")[1]
        calculated_sig = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, calculated_sig)
    except Exception as e:
        logger.warning(f"HMAC verification error: {e}")
        return False


@app.post("/webhook")
async def receive_fb_event(request: Request, background_tasks: BackgroundTasks):
    try:
        raw_body = await request.body()
        config = load_config()
        app_secret = config.get("fb_app_secret", "") or settings.fb_app_secret
        signature = request.headers.get("X-Hub-Signature-256")

        # Verify HMAC signature if app_secret is set
        if app_secret and not verify_meta_hmac_signature(raw_body, signature, app_secret):
            await log_message("Security", "Blocked unauthorized Facebook Webhook: Invalid HMAC-SHA256 signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

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


@app.post("/api/v3/simulator/chat")
async def simulator_chat_pipeline(payload: Dict[str, Any]):
    """
    Production-grade Simulator Pipeline with real fuzzy matching,
    deterministic grounding verification, and live SSE event emission.
    """
    t_start = time.time()
    try:
        message = payload.get("message", "").strip()
        channel = payload.get("channel", "whatsapp")

        await log_message("EVENT", f"Incoming {channel.upper()} simulation message: '{message}'", "text-sky-400")

        # 1. Real Fuzzy Search against Excel catalog
        fuzzy_result = excel_cache.search_product_fuzzy(message, min_threshold=0.50)
        found_product = None
        matched_raw = fuzzy_result.get("product")
        confidence = fuzzy_result.get("confidence", 0.0)

        if matched_raw:
            found_product = {
                "code": str(matched_raw.get("كود المنتج", "")),
                "name": str(matched_raw.get("اسم المنتج", "")),
                "price": float(matched_raw.get("السعر", 0.0) or 0.0),
                "stock": int(matched_raw.get("الكمية المتاحة", 1) or 1),
                "size": str(matched_raw.get("المقاس", "")),
                "color": str(matched_raw.get("اللون", ""))
            }
            await log_message(
                "FUZZY_SQL",
                f"Matched SKU '{found_product['code']}' ({found_product['name']}) with confidence: {confidence:.2f}",
                "text-emerald-400 font-semibold"
            )
        else:
            await log_message(
                "FUZZY_SQL",
                f"No catalog match found for query (Confidence: {confidence:.2f} < 0.50)",
                "text-amber-400"
            )

        # 2. Dynamic Scratch Flow Rules Evaluation
        custom_rules = []
        flow_path = Path(__file__).parent / "plugins" / "whatsapp_openwa" / "flow.json"
        active_flow_blocks = []
        if flow_path.exists():
            try:
                active_flow_blocks = json.loads(flow_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Check for Stock Guard rule
        for b in active_flow_blocks:
            b_id = b.get("id", "") or b.get("blockId", "")
            fields = b.get("fields", {}) or b.get("values", {})
            custom_prompt = b.get("customPrompt", "") or fields.get("rule_description", "")

            if b_id in ("data_stock_guard", "sql_stock_guard"):
                action_on_empty = fields.get("action_on_empty", "اعتذر فوراً عن نفاذ المنتج")
                if found_product and found_product.get("stock", 0) <= 0:
                    custom_rules.append(f"قاعدة نفاد المخزون الصارمة: المنتج '{found_product['name']}' نفدت كميته بالكامل (الكمية 0)، {action_on_empty} بلطف واعتذر عن عدم إمكانية الشراء حالياً.")

            elif custom_prompt:
                custom_rules.append(f"قاعدة مخصصة برمجها المستخدم (Qwen Rule): {custom_prompt}")

            elif b_id in ("offer_multi_discount", "custom_offer"):
                discount = fields.get("discount", "15%")
                shipping = fields.get("shipping", "شحن مجاني")
                if any(term in message for term in ["قطعتين", "اتنين", "2", "اثنين", "خصم", "عرض", "قطعتين"]):
                    custom_rules.append(f"قاعدة العروض الترويجية: العميل يطلب كمية/عرض، طبق خصم {discount} مع {shipping}.")

        # 3. AI Persona & Context Grounding
        config = load_config()
        system_prompt = config.get("system_prompt", "أنت موظف خدمة عملاء مصري ودود ولطيف جداً في متجر ملابس. تحدث بالعامية المصرية الودية.")
        
        context_parts = []
        if found_product:
            context_parts.append(f"بيانات المخزن (SQL): المنتج '{found_product['name']}' كود {found_product['code']} بسعر {found_product['price']} ج.م متوفر منه {found_product['stock']} قطعة.")
        else:
            context_parts.append("المنتج المطلوب غير محدد بالاسم، اسأل العميل بلطف عن الموديل أو المقاس.")

        for rule in custom_rules:
            context_parts.append(rule)

        full_prompt = f"{system_prompt}\n\n" + "\n".join(context_parts)
        messages = [
            {"role": "system", "content": full_prompt},
            {"role": "user", "content": message}
        ]

        reply = ""
        try:
            reply = await AIProviderManager.complete_chat(messages, config, temperature=0.6)
        except Exception as ai_err:
            logger.warning(f"Simulator AI generation fallback: {ai_err}")

        custom_offer = any("خصم" in r or "عروض" in r or "عرض" in r for r in custom_rules)

        prod_obj = ProductInfo(
            code=found_product["code"],
            name=found_product["name"],
            price=found_product["price"],
            size=found_product["size"],
            color=found_product["color"],
            quantity=found_product["stock"],
            description=""
        ) if found_product else None

        if reply:
            guarded_reply = verify_and_guard_grounding(reply, prod_obj, message)
        else:
            if found_product:
                offer_txt = " ولو طلبت قطعتين هتاخد خصم 15% وشحن مجاني! ✨" if custom_offer else ""
                guarded_reply = f"أهلاً بحضرتك يا فندم!  بخصوص {found_product['name']}، سعره {found_product['price']} جنيه ومتاح في المخزن.{offer_txt} تحب أحجزلك المقاس المناسب؟"
            else:
                guarded_reply = "أهلاً بيك يا فندم في M.A.R.K.E.T!  المنتج المطلوب غير متوفر حالياً في المخزن أو برجاء تزويدنا بكود المنتج للتأكد. ✨"

        elapsed_ms = int((time.time() - t_start) * 1000)
        await log_message("GROUNDING", f"Zero-Hallucination verification: Conf={confidence:.2f}, Latency={elapsed_ms}ms", "text-emerald-300 font-bold")
        await log_message("AI_REPLY", f"Sent Egyptian Arabic response ({channel}): \"{guarded_reply[:60]}...\"", "text-cyan-300")

        # Executed steps trace
        steps = [1, 2] # Event -> SQL
        if custom_offer or custom_rules:
            steps.append(3) # Custom logic / Qwen rule
        steps.append(4) # AI Core
        steps.append(5) # Action Dispatch

        return {
            "status": "success",
            "reply": guarded_reply,
            "product": found_product,
            "custom_offer": custom_offer,
            "executed_steps": steps,
            "channel": channel,
            "confidence": confidence,
            "latency_ms": elapsed_ms
        }
    except Exception as e:
        logger.error(f"Simulator chat error: {e}")
        return {
            "status": "error",
            "reply": f"عذراً، حدث خطأ في المحاكي: {str(e)}",
            "executed_steps": [1]
        }


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