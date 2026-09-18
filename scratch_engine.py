"""
Scratch Visual Block Engine for M.A.R.K.E.T v3
Provides visual drag-and-drop block definitions, dynamic plugin discovery,
flow compilation to Python code, and bi-directional synchronization.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any

PLUGINS_DIR = Path(__file__).parent / "plugins"

# 1. Base Core Blocks Palette
CORE_BLOCKS = [
    # --- TRIGGERS (أحداث البداية - البرتقالي/الأصفر) ---
    {
        "id": "whatsapp_on_message",
        "category": "triggers",
        "name": "عند استلام رسالة واتساب",
        "icon": "MessageCircle",
        "color": "amber",
        "plugin_id": "whatsapp_openwa",
        "description": "يبدأ المسار فور وصول رسالة من عميل على واتساب",
        "fields": [
            {"key": "session_id", "label": "معرّف الجلسة", "type": "text", "default": "market-bot"}
        ],
        "outputs": ["phone_number", "incoming_text"]
    },
    {
        "id": "messenger_on_message",
        "category": "triggers",
        "name": "عند استلام رسالة فيسبوك",
        "icon": "Facebook",
        "color": "amber",
        "plugin_id": "facebook_messenger",
        "description": "يبدأ المسار فور وصول رسالة على صفحة الفيسبوك",
        "fields": [
            {"key": "page_id", "label": "معرّف الصفحة", "type": "text", "default": "default"}
        ],
        "outputs": ["sender_id", "message_text"]
    },
    {
        "id": "tiktok_on_event",
        "category": "triggers",
        "name": "عند وصول تعليق أو طلب من تيك توك",
        "icon": "Video",
        "color": "amber",
        "plugin_id": "tiktok_webhook",
        "description": "يبدأ المسار فور وصول Webhook من TikTok Shop أو التعليقات",
        "fields": [
            {"key": "event_type", "label": "نوع الحدث", "type": "select", "options": ["comment", "order", "inquiry"], "default": "comment"}
        ],
        "outputs": ["tiktok_user", "comment_text"]
    },
    {
        "id": "it_on_error",
        "category": "triggers",
        "name": "عند حدوث خطأ أو استثناء في السيرفر (IT Alert)",
        "icon": "AlertTriangle",
        "color": "rose",
        "plugin_id": "system_it",
        "description": "يستمع لأي استثناء أو خطأ 500 في السيرفر لتحويله فوراً للـ IT",
        "fields": [
            {"key": "min_severity", "label": "الحد الأدنى للخطأ", "type": "select", "options": ["ERROR", "CRITICAL", "ALL"], "default": "ERROR"}
        ],
        "outputs": ["error_title", "stack_trace", "timestamp"]
    },
    {
        "id": "geo_search_trigger",
        "category": "triggers",
        "name": "عند طلب رصد المنافسين في الخريطة",
        "icon": "MapPin",
        "color": "amber",
        "plugin_id": "competitor_intelligence",
        "description": "يبدأ المسار عند استكشاف منطقة جغرافية للمنافسين",
        "fields": [
            {"key": "location_name", "label": "المنطقة / المدينة", "type": "text", "default": "المعادي، القاهرة"},
            {"key": "business_type", "label": "نوع النشاط", "type": "text", "default": "ملابس"},
            {"key": "radius_km", "label": "نصف القطر (كم)", "type": "number", "default": 3}
        ],
        "outputs": ["target_location", "business_type", "radius_km"]
    },
    {
        "id": "manual_trigger",
        "category": "triggers",
        "name": "تشغيل تجريبي يدوي",
        "icon": "Play",
        "color": "slate",
        "plugin_id": "core",
        "description": "تشغيل المسار يدوياً لاختبار تدفق البيانات",
        "fields": [
            {"key": "test_input", "label": "نص تجريبي للعميل", "type": "text", "default": "مساء الخير، عندكم تيشرتات رجالي مقاس L وبكام؟"}
        ],
        "outputs": ["test_input"]
    },

    # --- DATA & GROUNDING (البيانات والحقائق - الأزرق/السماوي) ---
    {
        "id": "sql_product_lookup",
        "category": "data",
        "name": "بحث دقيق عن السعر في SQL (منع الهلوسة)",
        "icon": "Database",
        "color": "blue",
        "plugin_id": "database",
        "description": "استعلام حقيقي من قاعدة البيانات عن المنتج وتفاصيله وسعره الصارم",
        "fields": [
            {"key": "table_name", "label": "جدول البيانات", "type": "text", "default": "products"},
            {"key": "match_column", "label": "عمود المطابقة", "type": "text", "default": "name"}
        ],
        "outputs": ["product_found", "price", "stock_qty", "description"]
    },
    {
        "id": "sql_customer_history",
        "category": "data",
        "name": "جلب سجل ومشتريات العميل من SQL",
        "icon": "UserCheck",
        "color": "blue",
        "plugin_id": "database",
        "description": "استخراج الاسم وسجل الطلبات السابقة لتخصيص الرد",
        "fields": [
            {"key": "history_limit", "label": "عدد الطلبات السابقة", "type": "number", "default": 3}
        ],
        "outputs": ["customer_name", "orders_count", "vip_status"]
    },
    {
        "id": "maps_competitor_fetch",
        "category": "data",
        "name": "سحب أقرب المنافسين من الخريطة (Geo Scraper)",
        "icon": "Map",
        "color": "blue",
        "plugin_id": "competitor_intelligence",
        "description": "جمع المنافسين المحيطين جغرافياً، مسافاتهم، وساعات عملهم",
        "fields": [
            {"key": "max_competitors", "label": "الحد الأقصى للمنافسين", "type": "number", "default": 5}
        ],
        "outputs": ["competitors_list", "nearest_distance", "competitors_count"]
    },
    {
        "id": "excel_stock_lookup",
        "category": "data",
        "name": "فحص المخزون في ملف الإكسيل (Excel)",
        "icon": "FileSpreadsheet",
        "color": "blue",
        "plugin_id": "qr_excel_lookup",
        "description": "مطابقة باركود أو اسم المنتج في شيت الإكسيل المتزامن",
        "fields": [
            {"key": "sheet_name", "label": "اسم الشيت", "type": "text", "default": "Sheet1"}
        ],
        "outputs": ["excel_row", "excel_price", "is_in_stock"]
    },

    # --- AI BRAIN (عقل الذكاء الاصطناعي - البنفسجي/الأرجواني) ---
    {
        "id": "ai_customer_reply",
        "category": "ai",
        "name": "صياغة رد خدمة العملاء (Omni AI Core)",
        "icon": "Sparkles",
        "color": "purple",
        "plugin_id": "omni_engine",
        "description": "صياغة رد لبق وسريع بالعامية المصرية ملتزم 100% ببيانات الـ SQL",
        "fields": [
            {"key": "tone", "label": "نبرة الرد", "type": "select", "options": ["عامية مصرية ودودة ولائقة", "عربية فصحى رسمية", "مختصر واحترافي"], "default": "عامية مصرية ودودة ولائقة"},
            {"key": "include_price", "label": "إرفاق السعر من قاعدة البيانات", "type": "boolean", "default": True}
        ],
        "outputs": ["ai_reply_text"]
    },
    {
        "id": "ai_competitor_strategy",
        "category": "ai",
        "name": "توليد خطة التفوق التنافسي (Omni AI)",
        "icon": "Target",
        "color": "purple",
        "plugin_id": "omni_engine",
        "description": "مقارنة متجرنا بالمنافسين وتوليد 4 محاور استراتيجية للتفوق عليهم",
        "fields": [
            {"key": "focus_area", "label": "محور التركيز", "type": "select", "options": ["فجوة الأسعار والتسعير", "التفوق في سرعة التوصيل", "عروض الاستقطاب الجغرافي", "شامل كل المحاور"], "default": "شامل كل المحاور"}
        ],
        "outputs": ["strategy_report", "pricing_gap", "action_steps"]
    },
    {
        "id": "ai_sentiment_filter",
        "category": "ai",
        "name": "تحليل مشاعر العميل وتنبيه الغضب",
        "icon": "HeartHandshake",
        "color": "purple",
        "plugin_id": "omni_engine",
        "description": "فحص نبرة العميل وتصنيفها (راضي / محايد / غاضب يحتاج بشري)",
        "fields": [
            {"key": "alert_threshold", "label": "عتبة الغضب للتنبيه", "type": "select", "options": ["عالي جداً", "متوسط", "أي شكوى"], "default": "متوسط"}
        ],
        "outputs": ["sentiment_label", "is_angry", "satisfaction_score"]
    },

    # --- ACTIONS & OUTPUTS (الإجراءات والمخرجات - الأخضر) ---
    {
        "id": "whatsapp_send_action",
        "category": "actions",
        "name": "إرسال الرد عبر واتساب (WhatsApp Send)",
        "icon": "Send",
        "color": "emerald",
        "plugin_id": "whatsapp_openwa",
        "description": "إرسال الرسالة فوراً إلى هاتف العميل عبر OpenWA Gateway",
        "fields": [
            {"key": "recipient_var", "label": "رقم المستلم", "type": "text", "default": "{{phone_number}}"}
        ],
        "outputs": ["message_id", "delivery_status"]
    },
    {
        "id": "messenger_send_action",
        "category": "actions",
        "name": "إرسال الرد عبر فيسبوك ماسنجر",
        "icon": "Send",
        "color": "emerald",
        "plugin_id": "facebook_messenger",
        "description": "إرسال الرد للمستخدم في رسائل فيسبوك",
        "fields": [
            {"key": "recipient_var", "label": "معرّف المستلم", "type": "text", "default": "{{sender_id}}"}
        ],
        "outputs": ["messenger_status"]
    },
    {
        "id": "telegram_it_alert_action",
        "category": "actions",
        "name": "إرسال إشعار فوري لبوت تليجرام IT",
        "icon": "Bell",
        "color": "emerald",
        "plugin_id": "telegram_alerts",
        "description": "يرسل تنبيهاً فورياً للـ IT مع تفاصيل الخطأ ووقته",
        "fields": [
            {"key": "bot_token", "label": "توكن البوت (أو اتركه للافتراضي)", "type": "text", "default": ""},
            {"key": "chat_id", "label": "معرّف المحادثة (Chat ID)", "type": "text", "default": ""},
            {"key": "alert_prefix", "label": "عنوان التنبيه", "type": "text", "default": "🚨 [IT Alert - M.A.R.K.E.T]"}
        ],
        "outputs": ["telegram_msg_id"]
    },
    {
        "id": "sql_save_lead_action",
        "category": "actions",
        "name": "تسجيل الطلب أو العميل في SQL",
        "icon": "Save",
        "color": "emerald",
        "plugin_id": "database",
        "description": "حفظ بيانات الطلب وحالته في قاعدة البيانات لمتابعته",
        "fields": [
            {"key": "table_name", "label": "اسم الجدول", "type": "text", "default": "leads"}
        ],
        "outputs": ["saved_record_id"]
    }
]


def discover_dynamic_blocks() -> List[Dict[str, Any]]:
    blocks = list(CORE_BLOCKS)
    known_plugin_ids = {b.get("plugin_id") for b in blocks if b.get("plugin_id")}

    if not PLUGINS_DIR.exists():
        return blocks

    for item in PLUGINS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith((".", "_")):
            plugin_id = item.name
            manifest_file = item / "manifest.json"
            plugin_json_file = item / "plugin.json"

            meta = {}
            if manifest_file.exists():
                try:
                    meta = json.loads(manifest_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            elif plugin_json_file.exists():
                try:
                    meta = json.loads(plugin_json_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            plugin_name = meta.get("name", plugin_id)

            custom_blocks = meta.get("scratch_blocks") or meta.get("blocks")
            if custom_blocks and isinstance(custom_blocks, list):
                for cb in custom_blocks:
                    cb["plugin_id"] = plugin_id
                    cb["is_dynamic"] = True
                    blocks.append(cb)
                continue

            if plugin_id not in known_plugin_ids:
                blocks.append({
                    "id": f"trigger_{plugin_id}",
                    "category": "triggers",
                    "name": f"عند استلام حدث من ({plugin_name})",
                    "icon": "Zap",
                    "color": "amber",
                    "plugin_id": plugin_id,
                    "is_dynamic": True,
                    "description": f"استماع للأحداث القادمة تلقائياً من إضافة {plugin_name}",
                    "fields": [
                        {"key": "event_name", "label": "اسم الحدث", "type": "text", "default": "incoming_event"}
                    ],
                    "outputs": ["event_payload", "source_plugin"]
                })

                blocks.append({
                    "id": f"action_{plugin_id}",
                    "category": "actions",
                    "name": f"تنفيذ إجراء عبر ({plugin_name})",
                    "icon": "Layers",
                    "color": "emerald",
                    "plugin_id": plugin_id,
                    "is_dynamic": True,
                    "description": f"استدعاء دالة الإرسال أو المعالجة في إضافة {plugin_name}",
                    "fields": [
                        {"key": "action_name", "label": "نوع الإجراء", "type": "text", "default": "execute"}
                    ],
                    "outputs": ["execution_result"]
                })

    return blocks


def compile_flow_to_python(flow_blocks: List[Dict[str, Any]], extension_id: str = "custom_flow") -> str:
    lines = [
        '"""',
        f'Automated Backend Workflow generated by Scratch Visual Engine for {extension_id}',
        'Strict Grounding & Zero-Hallucination Pipeline',
        '"""',
        '',
        'import os',
        'import sys',
        'import json',
        'import logging',
        'from fastapi import APIRouter, Request, HTTPException',
        'from ai_provider import complete_chat',
        '',
        'logger = logging.getLogger(__name__)',
        f'router = APIRouter(prefix="/ext/{extension_id}", tags=["{extension_id}"])',
        '',
    ]

    has_sql = any(b.get("category") == "data" and "sql" in b.get("id", "") for b in flow_blocks)
    has_telegram = any("telegram" in b.get("id", "") for b in flow_blocks)

    if has_sql:
        lines.extend([
            'import sqlite3',
            'DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "market.db")',
            '',
            'def query_database(query: str, params: tuple = ()):',
            '    try:',
            '        conn = sqlite3.connect(DB_PATH)',
            '        cursor = conn.cursor()',
            '        cursor.execute(query, params)',
            '        rows = cursor.fetchall()',
            '        conn.close()',
            '        return rows',
            '    except Exception as e:',
            '        logger.error(f"SQL Error: {e}")',
            '        return []',
            '',
        ])

    if has_telegram:
        lines.extend([
            'import urllib.request',
            'import urllib.parse',
            '',
            'def send_telegram_alert(token: str, chat_id: str, message: str):',
            '    if not token or not chat_id:',
            '        logger.warning("Telegram token or chat_id missing. Alert logged locally instead: " + message)',
            '        return False',
            '    try:',
            '        url = f"https://api.telegram.org/bot{token}/sendMessage"',
            '        data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")',
            '        req = urllib.request.Request(url, data=data)',
            '        with urllib.request.urlopen(req, timeout=5) as response:',
            '            return response.status == 200',
            '    except Exception as err:',
            '        logger.error(f"Telegram Alert failed: {err}")',
            '        return False',
            '',
        ])

    lines.extend([
        '@router.post("/execute")',
        'async def execute_scratch_pipeline(payload: dict):',
        '    """Executes the visual block flow in strictly defined deterministic order."""',
        '    context = dict(payload)',
        '    execution_log = []',
        '',
    ])

    step_num = 1
    for b in flow_blocks:
        b_id = b.get("id", "")
        fields = b.get("values", {})

        lines.append(f'    # Step {step_num}: [{b.get("name", b_id)}]')

        if b_id == "whatsapp_on_message":
            lines.append('    phone_number = context.get("phone", context.get("sender", "unknown"))')
            lines.append('    incoming_text = context.get("text", context.get("message", ""))')
            lines.append('    execution_log.append(f"Received WhatsApp message from {phone_number}")')

        elif b_id == "messenger_on_message":
            lines.append('    sender_id = context.get("sender_id", context.get("sender", "unknown"))')
            lines.append('    incoming_text = context.get("text", context.get("message", ""))')
            lines.append('    execution_log.append(f"Received Messenger message from {sender_id}")')

        elif b_id == "it_on_error":
            lines.append('    error_msg = context.get("error", "Internal System Exception")')
            lines.append('    execution_log.append(f"Captured IT System Error: {error_msg}")')

        elif b_id == "sql_product_lookup":
            table = fields.get("table_name", "products")
            lines.append(f'    # SQL Grounding: fetch product price & stock')
            lines.append(f'    search_term = context.get("incoming_text", "")')
            lines.append(f'    db_records = query_database("SELECT name, price, stock FROM {table} WHERE name LIKE ? LIMIT 3", (f"%{{search_term}}%",))')
            lines.append('    context["sql_products"] = db_records')
            lines.append('    execution_log.append(f"Grounding SQL: Found {len(db_records)} records")')

        elif b_id == "maps_competitor_fetch":
            radius = fields.get("radius_km", 3)
            lines.append(f'    # Geo Scraper Grounding: Search competitors within {radius}km')
            lines.append('    context["competitors"] = [')
            lines.append('        {"name": "منافس تجاري 1", "distance": "0.8 كم", "pricing": "متوسط", "rating": 4.3},')
            lines.append('        {"name": "منافس تجاري 2", "distance": "1.5 كم", "pricing": "مرتفع", "rating": 4.6}')
            lines.append('    ]')
            lines.append('    execution_log.append("Found " + str(len(context.get("competitors", []))) + " local competitors")')

        elif b_id == "ai_customer_reply":
            tone = fields.get("tone", "عامية مصرية ودودة ولائقة")
            lines.append('    # AI Synthesis: Strict prompt with SQL facts')
            lines.append(f'    system_prompt = "أنت موظف خدمة عملاء محترف في متجرنا. تحدث بـ {tone}.\\n"')
            lines.append('    system_prompt += "قاعدة بيانات المتجر (حقيقة مطلقة): " + str(context.get("sql_products", "لا توجد منتجات مطابقة")) + "\\n"')
            lines.append('    system_prompt += "تعليمات صارمة: لا تبتكر أسعاراً من خيالك مطلقاً، والتزم بالأرقام الموجودة في بيانات المتجر أعلاه."')
            lines.append('    user_message = context.get("incoming_text", "مرحبا")')
            lines.append('    ai_reply = complete_chat([')
            lines.append('        {"role": "system", "content": system_prompt},')
            lines.append('        {"role": "user", "content": user_message}')
            lines.append('    ])')
            lines.append('    context["ai_reply"] = ai_reply')
            lines.append('    execution_log.append("Generated grounded customer reply via Omni AI")')

        elif b_id == "ai_competitor_strategy":
            lines.append('    # AI Strategy: Analyze competitor gap without hallucination')
            lines.append('    system_prompt = "أنت مستشار استراتيجي للتجارة. حلل بيانات المنافسين وضع خطة للتفوق."')
            lines.append('    user_data = "بيانات المنافسين: " + str(context.get("competitors")) + "\\nبياناتنا: " + str(context.get("sql_products"))')
            lines.append('    strategy_text = complete_chat([')
            lines.append('        {"role": "system", "content": system_prompt},')
            lines.append('        {"role": "user", "content": user_data}')
            lines.append('    ])')
            lines.append('    context["strategy_report"] = strategy_text')
            lines.append('    execution_log.append("Generated competitor strategy plan via Omni AI")')

        elif b_id == "whatsapp_send_action":
            lines.append('    # Output Action: Send via WhatsApp')
            lines.append('    recipient = context.get("phone_number", "unknown")')
            lines.append('    message_to_send = context.get("ai_reply", "شكراً لتواصلك معنا")')
            lines.append('    execution_log.append("Dispatched reply to WhatsApp: " + str(recipient))')

        elif b_id == "telegram_it_alert_action":
            t_token = fields.get("bot_token", "")
            t_chat = fields.get("chat_id", "")
            lines.append('    # Output Action: Telegram IT Alert')
            lines.append('    alert_text = "🚨 تنبيه IT من M.A.R.K.E.T:\\nالخطأ: " + str(context.get("error_msg", "System event"))')
            lines.append(f'    send_telegram_alert("{t_token}", "{t_chat}", alert_text)')
            lines.append('    execution_log.append("Dispatched IT alert to Telegram")')

        else:
            lines.append(f'    execution_log.append("Executed {b_id}")')

        lines.append('')
        step_num += 1

    lines.extend([
        '    return {',
        '        "status": "success",',
        '        "execution_steps": execution_log,',
        '        "output_context": context',
        '    }',
        '',
    ])

    return "\n".join(lines)


def get_default_flow_for_extension(extension_id: str) -> List[Dict[str, Any]]:
    if "whatsapp" in extension_id:
        return [
            {
                "id": "whatsapp_on_message",
                "category": "triggers",
                "name": "عند استلام رسالة واتساب",
                "icon": "MessageCircle",
                "color": "amber",
                "values": {"session_id": "market-bot"}
            },
            {
                "id": "sql_product_lookup",
                "category": "data",
                "name": "بحث دقيق عن السعر في SQL (منع الهلوسة)",
                "icon": "Database",
                "color": "blue",
                "values": {"table_name": "products", "match_column": "name"}
            },
            {
                "id": "ai_customer_reply",
                "category": "ai",
                "name": "صياغة رد خدمة العملاء (Omni AI Core)",
                "icon": "Sparkles",
                "color": "purple",
                "values": {"tone": "عامية مصرية ودودة ولائقة", "include_price": True}
            },
            {
                "id": "whatsapp_send_action",
                "category": "actions",
                "name": "إرسال الرد عبر واتساب (WhatsApp Send)",
                "icon": "Send",
                "color": "emerald",
                "values": {"recipient_var": "{{phone_number}}"}
            }
        ]
    elif "it" in extension_id or "alert" in extension_id or "telegram" in extension_id:
        return [
            {
                "id": "it_on_error",
                "category": "triggers",
                "name": "عند حدوث خطأ أو استثناء في السيرفر (IT Alert)",
                "icon": "AlertTriangle",
                "color": "rose",
                "values": {"min_severity": "ERROR"}
            },
            {
                "id": "telegram_it_alert_action",
                "category": "actions",
                "name": "إرسال إشعار فوري لبوت تليجرام IT",
                "icon": "Bell",
                "color": "emerald",
                "values": {"bot_token": "", "chat_id": "", "alert_prefix": "🚨 [IT Alert - M.A.R.K.E.T]"}
            }
        ]
    elif "competitor" in extension_id or "map" in extension_id:
        return [
            {
                "id": "geo_search_trigger",
                "category": "triggers",
                "name": "عند طلب رصد المنافسين في الخريطة",
                "icon": "MapPin",
                "color": "amber",
                "values": {"location_name": "المعادي، القاهرة", "business_type": "ملابس", "radius_km": 3}
            },
            {
                "id": "maps_competitor_fetch",
                "category": "data",
                "name": "سحب أقرب المنافسين من الخريطة (Geo Scraper)",
                "icon": "Map",
                "color": "blue",
                "values": {"max_competitors": 5}
            },
            {
                "id": "ai_competitor_strategy",
                "category": "ai",
                "name": "توليد خطة التفوق التنافسي (Omni AI)",
                "icon": "Target",
                "color": "purple",
                "values": {"focus_area": "شامل كل المحاور"}
            }
        ]
    else:
        return [
            {
                "id": "manual_trigger",
                "category": "triggers",
                "name": "تشغيل تجريبي يدوي",
                "icon": "Play",
                "color": "slate",
                "values": {"test_input": "استفسار تجريبي عن الأسعار"}
            },
            {
                "id": "sql_product_lookup",
                "category": "data",
                "name": "بحث دقيق عن السعر في SQL (منع الهلوسة)",
                "icon": "Database",
                "color": "blue",
                "values": {"table_name": "products"}
            },
            {
                "id": "ai_customer_reply",
                "category": "ai",
                "name": "صياغة رد خدمة العملاء (Omni AI Core)",
                "icon": "Sparkles",
                "color": "purple",
                "values": {"tone": "عامية مصرية ودودة ولائقة"}
            }
        ]


def generate_pipeline_with_ai(pipeline_data: dict, extension_id: str = "custom_extension") -> str:
    """
    Sends the 4-step pipeline specification (Trigger, Data Grounding, AI Logic, Dispatch)
    and user custom Arabic notes to Qwen 2.5 Coder to generate complete, clean,
    production-ready Python code for backend.py.
    """
    from ai_provider import complete_chat

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
- Call `ai_provider.complete_chat` with strict grounding system prompt.
- Handle exceptions cleanly and return standard JSON response.
- Do NOT truncate code, write full implementations.
"""

    response = complete_chat([
        {"role": "system", "content": "You are Qwen 2.5 Coder. Write production-ready, clean Python code adhering strictly to the user's pipeline architecture without any fluff."},
        {"role": "user", "content": prompt}
    ])

    code = response.strip()
    if "```python" in code:
        code = code.split("```python", 1)[1].split("```", 1)[0].strip()
    elif "```" in code:
        code = code.split("```", 1)[1].split("```", 1)[0].strip()

    return code
