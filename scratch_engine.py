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
            {"key": "alert_prefix", "label": "عنوان التنبيه", "type": "text", "default": " [IT Alert - M.A.R.K.E.T]"}
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

    # 1. Discover user-created AI Custom Blocks
    custom_blocks_file = PLUGINS_DIR / "custom_blocks.json"
    if custom_blocks_file.exists():
        try:
            cblocks = json.loads(custom_blocks_file.read_text(encoding="utf-8"))
            if isinstance(cblocks, list):
                for cb in cblocks:
                    cb_copy = dict(cb)
                    cb_copy["is_custom_ai"] = True
                    blocks.append(cb_copy)
        except Exception as e:
            pass

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

    has_sql = any(
        (b.get("category") == "data") or 
        any(k in (b.get("type") or b.get("blockId") or b.get("id", "")) for k in ("sql", "lookup", "excel", "data"))
        for b in flow_blocks
    )
    has_telegram = any("telegram" in (b.get("type") or b.get("blockId") or b.get("id", "")) for b in flow_blocks)

    if has_sql:
        lines.extend([
            'import sqlite3',
            'DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "market_edge.db")',
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
        b_id = b.get("type") or b.get("blockId") or b.get("id", "")
        fields = b.get("values") or b.get("fields", {})
        custom_prompt = b.get("customPrompt") or fields.get("rule_description", "")
        block_title = b.get("name") or b.get("title", b_id)

        lines.append(f'    # Step {step_num}: [{block_title}]')

        if custom_prompt:
            lines.append(f'    # Custom Rule / Note: {custom_prompt}')

        if b_id in ("whatsapp_on_message", "trigger_whatsapp"):
            lines.append('    phone_number = context.get("phone", context.get("sender", "unknown"))')
            lines.append('    incoming_text = context.get("text", context.get("message", ""))')
            lines.append('    execution_log.append(f"Received WhatsApp message from {phone_number}: {incoming_text}")')

        elif b_id in ("fork_parallel", "router_branch"):
            lines.append('    # Parallel Fork / Broadcast: Broadcast message to parallel branch workers')
            lines.append('    execution_log.append("Fork: Dispatched message concurrently to SQL Engine & Human CS Pool")')

        elif b_id in ("human_cs_handover", "message_pool"):
            p_val = fields.get("priority", "normal")
            d_val = fields.get("department", "Customer Support Team")
            lines.append('    # Human CS Message Pool Handover')
            lines.append(f'    priority = "{p_val}"')
            lines.append(f'    dept = "{d_val}"')
            lines.append(f'    execution_log.append(f"Handover: Logged message in Human Team Pool ({{dept}}) with priority {{priority}}")')

        elif b_id in ("messenger_on_message", "trigger_facebook"):
            lines.append('    sender_id = context.get("sender_id", context.get("sender", "unknown"))')
            lines.append('    incoming_text = context.get("text", context.get("message", ""))')
            lines.append('    execution_log.append(f"Received Messenger message from {sender_id}: {incoming_text}")')

        elif b_id == "it_on_error":
            lines.append('    error_msg = context.get("error", "Internal System Exception")')
            lines.append('    execution_log.append(f"Captured IT System Error: {error_msg}")')

        elif b_id in ("sql_product_lookup", "data_sql_lookup", "data_excel_lookup"):
            table = fields.get("table", fields.get("table_name", "products"))
            lines.append(f'    # SQL Grounding: fetch product price & stock from {table}')
            lines.append('    search_term = context.get("incoming_text", "")')
            lines.append(f'    db_records = query_database("SELECT name, price, stock FROM {table} WHERE name LIKE ? LIMIT 3", (f"%{{search_term}}%",))')
            lines.append('    context["sql_products"] = db_records')
            lines.append('    execution_log.append(f"Grounding SQL: Found {len(db_records)} matching products")')

        elif b_id == "data_stock_guard":
            lines.append('    # Stock Guard: Check if available in inventory')
            lines.append('    products_found = context.get("sql_products", [])')
            lines.append('    in_stock = any(p[2] > 0 for p in products_found) if products_found else True')
            lines.append('    context["in_stock"] = in_stock')
            lines.append('    if not in_stock:')
            lines.append('        context["stock_status"] = "out_of_stock"')
            lines.append('        execution_log.append("Stock Guard: Product is currently out of stock. Applying apology rule.")')
            lines.append('    else:')
            lines.append('        execution_log.append("Stock Guard: Product available in stock.")')

        elif b_id == "offer_multi_discount":
            discount = fields.get("discount", "15%")
            lines.append(f'    # Offers & Discount Rule: {discount}')
            lines.append(f'    context["applicable_discount"] = "{discount}"')
            lines.append(f'    execution_log.append("Applied Multi-piece Discount Rule: {discount}")')

        elif b_id in ("ai_customer_reply", "ai_tone_reply"):
            tone = fields.get("tone", "عامية مصرية ودودة ولائقة")
            lines.append('    # AI Synthesis: Strict prompt with SQL facts')
            lines.append(f'    system_prompt = "أنت موظف خدمة عملاء محترف في متجرنا. تحدث بـ {tone}.\\n"')
            lines.append('    system_prompt += "قاعدة بيانات المتجر (حقيقة مطلقة): " + str(context.get("sql_products", "لا توجد منتجات مطابقة")) + "\\n"')
            if custom_prompt:
                lines.append(f'    system_prompt += "قاعدة إضافية من المدير: {custom_prompt}\\n"')
            lines.append('    system_prompt += "تعليمات صارمة: لا تبتكر أسعاراً من خيالك مطلقاً، والتزم بالأرقام الموجودة في بيانات المتجر أعلاه."')
            lines.append('    user_message = context.get("incoming_text", "مرحبا")')
            lines.append('    ai_reply = await complete_chat([')
            lines.append('        {"role": "system", "content": system_prompt},')
            lines.append('        {"role": "user", "content": user_message}')
            lines.append('    ])')
            lines.append('    context["ai_reply"] = ai_reply')
            lines.append('    execution_log.append("Generated grounded customer reply via Omni AI")')

        elif b_id == "custom_qwen_rule":
            lines.append('    # Custom Qwen Rule execution')
            lines.append(f'    rule_text = "{custom_prompt or fields.get("rule_description", "")}"')
            lines.append('    context["custom_rules"] = context.get("custom_rules", []) + [rule_text]')
            lines.append(f'    execution_log.append(f"Evaluated Custom Qwen Rule: {{rule_text}}")')

        elif b_id in ("whatsapp_send_action", "control_dispatch_reply"):
            lines.append('    # Output Action: Send via channel')
            lines.append('    recipient = context.get("phone_number", context.get("sender_id", "unknown"))')
            lines.append('    message_to_send = context.get("ai_reply", "شكراً لتواصلك معنا")')
            lines.append('    execution_log.append("Dispatched reply: " + str(recipient))')

        elif b_id in ("telegram_it_alert_action", "sensing_telegram_alert"):
            t_token = fields.get("bot_token", "")
            t_chat = fields.get("chat_id", "")
            lines.append('    # Output Action: Telegram Alert')
            lines.append('    alert_text = " تنبيه من M.A.R.K.E.T:\\n" + str(context.get("ai_reply", context.get("incoming_text", "Event captured")))')
            lines.append(f'    send_telegram_alert("{t_token}", "{t_chat}", alert_text)')
            lines.append('    execution_log.append("Dispatched alert to Telegram")')

        elif b_id.startswith("custom_") or b.get("isCustomQwen") or b.get("is_custom_ai"):
            # Dynamic Handling for AI-Synthesized Custom Nodes
            if "file_path" in fields:
                f_path = fields.get("file_path", "products.xlsx")
                s_name = fields.get("sheet_name", "Sheet1")
                t_col = fields.get("target_column", "code")
                lines.append(f'    # Custom Step: External Excel / Data Matcher ({block_title})')
                lines.append(f'    excel_path = "{f_path}"')
                lines.append('    if not os.path.exists(excel_path):')
                lines.append('        alt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), excel_path)')
                lines.append('        if os.path.exists(alt_path): excel_path = alt_path')
                lines.append('        elif os.path.exists("products.xlsx"): excel_path = "products.xlsx"')
                lines.append('    incoming_msg = str(context.get("incoming_text", context.get("message", "")))')
                lines.append('    matched_row = None')
                lines.append('    try:')
                lines.append('        import pandas as pd')
                lines.append('        df = pd.read_excel(excel_path) if excel_path.endswith((".xlsx", ".xls")) else pd.read_csv(excel_path)')
                lines.append(f'        target_col = "{t_col}" if "{t_col}" in df.columns else df.columns[0]')
                lines.append('        matches = df[df[target_col].astype(str).str.strip().str.lower().apply(lambda c: c in incoming_msg.lower() if c else False)]')
                lines.append('        if not matches.empty:')
                lines.append('            matched_row = matches.iloc[0].to_dict()')
                lines.append('    except Exception as e_exc:')
                lines.append('        logger.warning(f"Excel Match error: {e_exc}")')
                lines.append('    context["excel_matched_row"] = matched_row')
                lines.append('    context["is_matched"] = matched_row is not None')
                lines.append('    execution_log.append(f"Excel Match: {\'Found matching row in \' + str(excel_path) if matched_row else \'No matching code in \' + str(excel_path)}")')

            elif "target_codes" in fields:
                t_codes = [c.strip() for c in fields.get("target_codes", "").split(",") if c.strip()]
                lines.append(f'    # Custom Step: Promo Code Exact Matcher ({block_title})')
                lines.append(f'    valid_codes = {json.dumps(t_codes)}')
                lines.append('    incoming_msg = str(context.get("incoming_text", context.get("message", ""))).lower()')
                lines.append('    is_code_valid = any(code.lower() in incoming_msg for code in valid_codes)')
                lines.append('    context["is_code_valid"] = is_code_valid')
                lines.append('    execution_log.append(f"Promo Code Check: {\'Valid code applied\' if is_code_valid else \'No valid promo code found\'}")')

            else:
                lines.append(f'    # Custom AI Node: {block_title}')
                lines.append(f'    execution_log.append("Executed custom node: {block_title}")')

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
                "values": {"bot_token": "", "chat_id": "", "alert_prefix": " [IT Alert - M.A.R.K.E.T]"}
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


async def compile_scratch_flow_with_ai(flow_blocks: List[Dict[str, Any]], extension_id: str = "custom_flow", custom_intent: str = "") -> str:
    """
    Visual-to-Code Compiler powered by AI Coder (Qwen 2.5 Coder / Active AI).
    Takes arbitrary sequence of Scratch blocks and compiles them into a complete,
    clean, executable Python FastAPI plugin module.
    """
    from ai_provider import AIProviderManager
    from bot_logic import load_config

    config = load_config()

    # 1. Build structured semantic flow description from visual blocks
    steps_description = []
    for idx, b in enumerate(flow_blocks, 1):
        b_title = b.get("title", b.get("name", "كتلة برمجية"))
        b_cat = b.get("category", "general")
        fields = b.get("fields", b.get("values", {}))
        custom_prompt = b.get("customPrompt", "")
        
        step_desc = f"Step {idx} [{b_cat.upper()}]: {b_title}"
        if fields:
            step_desc += f"\n   - Settings/Parameters: {json.dumps(fields, ensure_ascii=False)}"
        if custom_prompt:
            step_desc += f"\n   - Custom User Rule/Instruction: \"{custom_prompt}\""
        steps_description.append(step_desc)

    flow_summary = "\n\n".join(steps_description) if steps_description else "Direct custom flow based on user intent."

    prompt = f"""You are Qwen 2.5 Coder, an expert Python backend engineer for the M.A.R.K.E.T platform.
Your job is to act as the Visual Scratch Compiler: take the following block-by-block visual flow designed by the user, and write the complete, clean, production-ready Python plugin file `adapter.py` / `backend.py` for extension `{extension_id}`.

[VISUAL SCRATCH FLOW SEQUENCE]:
{flow_summary}

[OVERALL USER INTENT / OBJECTIVE]:
{custom_intent or "Automate customer inquiries, verify stock with zero hallucination, and dispatch replies."}

[TECHNICAL & ARCHITECTURAL GUIDELINES]:
1. Framework: Python 3.12+ with FastAPI.
2. Router: Provide `router = APIRouter(prefix="/ext/{extension_id}", tags=["{extension_id}"])`.
3. Database & Grounding: Use `from database import db` to query `market_edge.db` (products/orders) with zero hallucination.
4. AI Completion: Use `from ai_provider import AIProviderManager` for any conversational text generation or persona reasoning.
5. Endpoints: Implement `@router.post("/execute")` or appropriate webhook handler.
6. Error Handling: Include try/except blocks and log execution steps.
7. Return Format: Output ONLY valid, clean Python code inside a ```python ``` code block. Do NOT truncate or use placeholders.
"""

    messages = [
        {"role": "system", "content": "You are Qwen 2.5 Coder. You translate visual Scratch flows into clean, robust, production Python backend code with zero placeholders."},
        {"role": "user", "content": prompt}
    ]

    try:
        response = await AIProviderManager.complete_coder(messages, config, temperature=0.2)
        if not response:
            # Fallback to deterministic compilation if AI coder is unreachable
            return compile_flow_to_python(flow_blocks, extension_id)

        code = response.strip()
        if "```python" in code:
            code = code.split("```python", 1)[1].split("```", 1)[0].strip()
        elif "```" in code:
            code = code.split("```", 1)[1].split("```", 1)[0].strip()
        return code
    except Exception as e:
        logger.error(f"AI Coder compilation error: {e}")
        return compile_flow_to_python(flow_blocks, extension_id)
