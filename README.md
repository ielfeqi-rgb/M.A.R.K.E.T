# M.A.R.K.E.T AI Platform (v3.0)

> **M.A.R.K.E.T**: Modular Automated Response & Knowledge Engine for Trade  
> Autonomous E-Commerce & Customer Service Infrastructure powered by Omni Engine.

---

## English Documentation

### Overview

**M.A.R.K.E.T** is an open-source, offline-first AI infrastructure designed to automate e-commerce operations, customer communications, inventory querying, and runtime extension deployment.

Powered natively by the **Omni Engine Core (`omni_engine`)**, the platform runs completely on local hardware or connects across a private network to a dedicated inference node using standard OpenAI-compatible REST endpoints.

---

### Core Capabilities in v3.0

1. **Omni Engine as Primary AI Core**
   - **Native Rust Inference**: Fast, predictable execution leveraging `omni_engine` built over `llama.cpp`.
   - **Distributed & Remote Setup**: Deploy `omni_engine` on an independent GPU/CPU server on your LAN, routing queries with zero local overhead (`custom_ai_url: "http://<REMOTE_IP>:8081/v1"`).
   - **Multi-Model Isolation**: Independent routing for programming tasks (Qwen 2.5 Coder) and customer conversations without state collisions.

2. **v3 Extension Studio & Automated Verification**
   - Integrated development workspace featuring live file inspection, syntax checks, and router mounting.
   - **Self-Healing Feedback Loop**: Automatically captures syntax and schema exceptions during generation, prompting immediate automated correction.
   - Dynamic tab registration into the control dashboard without restarting services.

3. **Multi-Channel Integrations**
   - **WhatsApp**: Direct integration via OpenWA Gateway with on-screen QR session pairing, automated webhooks, and purchase confirmations.
   - **Facebook Messenger & Comments**: Automated public comment replies and private inbox routing.
   - **TikTok & Barcode Vision**: Webhook listeners and computer vision QR/barcode inventory verification.

4. **Reliability Fallback Hierarchy**
   - **Level 1**: Omni Engine / Custom Endpoint (Local or Network Host).
   - **Level 2**: Embedded Process Supervisor.
   - **Level 3**: Managed Cloud APIs (Google Gemini, Groq, OpenAI, DeepSeek).
   - **Level 4**: Deterministic Rule Engine ensuring continuous uptime.

---

### Repository Structure

```
M.A.R.K.E.T/
├── main.py              # Application server, REST endpoints, and webhook routing
├── plugin_manager.py    # Runtime extension loader and dynamic router mount
├── ai_provider.py       # Inference client layer and fallback orchestration
├── llamacpp_manager.py  # Local server process supervisor
├── bot_logic.py         # Conversational routing, session context, and templates
├── hardware_detector.py # Hardware profile and memory diagnostic utilities
├── excel_helper.py      # Inventory spreadsheet read/write manager
├── http_client.py       # Shared asynchronous HTTP connection pool
├── qr_detector.py       # Computer vision barcode and QR decoding
├── settings.py          # Environment configuration models
├── config.json          # Persistent runtime configuration
├── products.xlsx        # Default catalog dataset
├── plugins/             # Active v3 production extensions
│   ├── whatsapp_openwa/     # WhatsApp integration extension
│   ├── facebook_messenger/  # Meta Messenger & Feed extension
│   ├── tiktok_webhook/      # TikTok commerce webhook handler
│   └── qr_excel_lookup/     # Inventory lookup and barcode scanner
├── plugins_backup/      # Extension templates and archived modules
└── static/              # Compiled single-page IDE and dashboard interface
```

---

### Quick Start

```bash
# Clone the repository
git clone https://github.com/ielfeqi-rgb/M.A.R.K.E.T.git
cd M.A.R.K.E.T

# Install Python dependencies
pip install -r requirements.txt

# Start the application server
python main.py
```

Open the dashboard in your browser: `http://localhost:8000`

---

### Distributed Deployment (Remote Omni Engine)

To offload AI inference to a dedicated node:
1. Start `omni_engine` on the target machine:
   ```bash
   ./omni_engine serve --port 8081
   ```
2. Set the target endpoint in M.A.R.K.E.T (`config.json` or Dashboard Settings):
   ```json
   {
     "ai_provider": "custom",
     "custom_ai_url": "http://192.168.1.100:8081/v1",
     "custom_ai_key": "optional_auth_key"
   }
   ```
All conversational and code generation tasks will route to the remote server automatically.

---

### License

This software is distributed under the **PolyForm NonCommercial License 1.0.0 (CC BY-NC-SA 4.0)**:
- Permitted for personal, educational, and non-commercial evaluation.
- Commercial production deployments require authorization from the author.

---

## التوثيق باللغة العربية (Arabic Documentation)

### نظرة عامة

منصة **M.A.R.K.E.T (v3.0)** هي بنية تحتية برمجية مفتوحة المصدر لإدارة التجارة الإلكترونية، وأتمتة الرد على العملاء عبر قنوات البيع الرقمية، وإدارة المخزون والتطوير البرمجي للإضافات، مدعومة بمحرك **Omni Engine**.

### الخصائص الرئيسية في الإصدار v3.0:
1. **الاعتماد على محرك Omni Engine**:
   - محرك استدلال محلي عالي الكفاءة مجمع بلغة Rust.
   - دعم التوزيع الشبكي لتشغيل المحرك على خادم مستقل والربط معه عبر الـ API (`custom_ai_url`).
2. **استوديو الإضافات ونظام التصحيح الذاتي**:
   - بيئة تطوير متكاملة لكتابة واختبار الإضافات بالواجهة والـ Backend.
   - نظام **Self-Healing Feedback Loop** للتحقق من سلامة الكود وإصلاح الأخطاء البرمجية تلقائياً.
3. **التكامل مع قنوات التواصل**:
   - دعم رسمي لبوابة واتساب ومسح رمز الـ QR مباشرة من اللوحة.
   - دعم تكامل فيسبوك ماسنجر والتعليقات وويب هوك تيك توك ومطابقة المخزون.

---

> **M.A.R.K.E.T AI Systems — 2026**
