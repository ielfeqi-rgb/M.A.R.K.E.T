# 🚀 M.A.R.K.E.T AI Platform (v3.0 — IDE & Extension Studio)

> **M.A.R.K.E.T**: **M**ulti-AI **A**utomated **R**esponse & **K**nowledge **E**ngine for **T**rade  
> *Official Open-Source Documentation for M.A.R.K.E.T AI — Autonomous E-Commerce & Customer Service Engine powered by Omni Engine v3.0*

---

## 📖 English Documentation (Primary)

### 🌟 What is M.A.R.K.E.T AI (v3.0)?

**M.A.R.K.E.T** (**M**ulti-AI **A**utomated **R**esponse & **K**nowledge **E**ngine for **T**rade) is an open-source, privacy-first, offline-capable AI infrastructure engineered to automate e-commerce customer service, multi-channel commerce (WhatsApp, Meta Facebook Messenger, TikTok Webhooks), Excel inventory lookups, QR code scanning, and dynamic v3 Extension Studio apps.

Powered natively by the **Omni Engine Core (`omni_engine`)**, M.A.R.K.E.T runs 100% locally on your hardware or connects across the local network to an external Omni Engine server via high-performance OpenAI-compatible REST endpoints.

---

### ✨ What's New in v3.0

1. **Omni Engine as Primary AI Core**:
   - **Native Rust Inference**: Fast, low-latency execution via `omni_engine` wrapping `llama.cpp`.
   - **Remote Host / Network Deployment**: Deploy `omni_engine` on a separate machine or dedicated server and connect M.A.R.K.E.T seamlessly over the network (`custom_ai_url: "http://<REMOTE_IP>:8081/v1"`).
   - **Multi-Model Concurrency**: Dedicated coding models (Qwen 2.5 Coder) for extension creation run concurrently with customer care conversational models.

2. **v3 Extension Studio & AI Box**:
   - Built-in IDE with real-time file tree, interactive code editor, and live syntax verification.
   - **Automated Self-Healing Feedback Loop**: Code generation automatically captures Python syntax errors or JSON formatting issues and prompts the model to self-repair instantly.
   - Dynamic tab mounting into the main dashboard navigation without restarting the application.

3. **Multi-Channel Commerce Gateway**:
   - **WhatsApp**: Native OpenWA Gateway integration with session QR code rendering, webhook sync, and purchase confirmation triggers.
   - **Facebook Messenger & Feed**: Instant comment auto-replies + private DM upsells.
   - **TikTok Webhooks & QR Scanner**: Multi-platform event listening and barcode/QR catalog lookups.

4. **Multi-AI Fallback Chain**:
   - **Priority 1**: Omni Engine / Custom Endpoint (`http://localhost:8081/v1` or Remote Host).
   - **Priority 2**: Local llama-server supervisor auto-detection.
   - **Priority 3**: Cloud Fallbacks (Google Gemini 2.5 Flash, Groq Llama 3.3 70B, OpenAI GPT-4o Mini, DeepSeek Chat).
   - **Priority 4**: Deterministic Rule-Based Fallback.

---

### 📁 Project Architecture

```
M.A.R.K.E.T/
├── main.py              # FastAPI Web Server, Webhooks & REST Endpoints (v3.0)
├── plugin_manager.py    # Dynamic v3 Extension Engine & Router Mounter
├── ai_provider.py       # Omni Engine Primary Core & Multi-AI Fallback Chain
├── llamacpp_manager.py  # Local llama-server Process Supervisor
├── bot_logic.py         # Customer Service Dialog Engine & Context Cache
├── hardware_detector.py # Hardware Spec Analyzer (RAM & CPU Cores)
├── excel_helper.py      # openpyxl Inventory Database Engine
├── http_client.py       # Connection Pooling & Async HTTP Client
├── qr_detector.py       # OpenCV Image QR Code Reader
├── settings.py          # Environment Variables & Pydantic Config
├── config.json          # Live Dashboard Config Storage
├── products.xlsx        # Default Excel Inventory File
├── plugins/             # Active v3 Extensions
│   ├── whatsapp_openwa/     # WhatsApp Gateway Channel Extension
│   ├── facebook_messenger/  # Facebook Messenger & Feed Extension
│   ├── tiktok_webhook/      # TikTok Commerce Webhook Extension
│   └── qr_excel_lookup/     # QR Code Scanner & Inventory Extension
├── plugins_backup/      # Archived Community & Official Extension Templates
└── static/              # Modern v3 Single-Page IDE & Dashboard
```

---

### ⚙️ Quick Start & Installation

```bash
# 1. Clone repository
git clone https://github.com/ielfeqi-rgb/M.A.R.K.E.T.git
cd M.A.R.K.E.T

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch M.A.R.K.E.T Server
python main.py
```

Access the Web Dashboard at: `http://localhost:8000`

---

### 🌐 Connecting to a Remote Omni Engine

To run `omni_engine` on a separate server or machine:
1. Start `omni_engine` on the remote device:
   ```bash
   ./omni_engine serve --port 8081
   ```
2. In M.A.R.K.E.T `config.json` (or via Dashboard Settings):
   ```json
   {
     "ai_provider": "custom",
     "custom_ai_url": "http://192.168.1.100:8081/v1",
     "custom_ai_key": "your_api_key_if_configured"
   }
   ```
M.A.R.K.E.T will route all customer service and extension generation queries directly to the remote Omni Engine instance with zero local CPU overhead.

---

### 📜 License & Terms of Use

This project is released under the **Non-Commercial Public License (PolyForm NonCommercial 1.0.0 / CC BY-NC-SA 4.0)**:

- **Free for Personal, Educational, and Non-Profit Use**: Individuals, students, researchers, and open-source developers can freely use, modify, and distribute this software for personal or non-profit purposes.
- **Commercial & Corporate Use Requires Permission**: Commercial businesses, for-profit entities, or individuals utilizing this software for commercial gain must obtain an explicit commercial license from the project owner.

*Copyright (c) 2026 M.A.R.K.E.T AI Systems (OmniContext Engine).*r commercial gain must obtain an explicit commercial license from the project owner.

*Copyright (c) 2026 M.A.R.K.E.T AI Systems (OmniContext Engine).*

---

## 📜 التوثيق باللغة العربية (Arabic Summary)

### 🎯 منصة M.A.R.K.E.T AI الإصدار الثالث (v3.0)

منصة **M.A.R.K.E.T AI (v3.0)** هي بنية تحتية متكاملة ومفتوحة المصدر لإدارة التجارة الإلكترونية وأتمتة خدمة العملاء وقنوات البيع المختلفة (واتساب، فيسبوك، تيك توك، إنستجرام)، معتمدة بالكامل على محرك **Omni Engine** المكتوب بلغة Rust.

### 🌟 أبرز التحديثات في الإصدار v3.0:
1. **محرك Omni Engine كمحرك أساسي**:
   - يعمل كمحرك ذكاء اصطناعي محلي فائق السرعة مبني بلغة Rust.
   - إمكانية تشغيله على جهاز آخر في الشبكة وربط السيرفر به عبر الـ API بكل سهولة (`custom_ai_url`).
2. **استوديو الإضافات v3 والتوليد بالأوامر العامية المباشرة**:
   - دعم كامل لإنشاء وتعديل الإضافات المتكاملة (Backend + UI + Manifest) عبر الأوامر العامية المباشرة من لوحة التحكم.
   - نظام **Self-Healing Feedback Loop** لمعالجة الأخطاء البرمجية ذاتياً وإصلاحها تلقائياً بالذكاء الاصطناعي.
3. **تكامل قنوات المبيعات المتعددة**:
   - ربط بوابة واتساب الرسمية (OpenWA) ومسح QR Code من لوحة التحكم مباشرة.
   - دعم ويب هوك تيك توك ومحرك قراءة أكواد QR والباركود وربطها بمخزون الإكسيل.

---

> **M.A.R.K.E.T Systems Documentation © 2026**  
> *OmniContext AI Core Engineering Team*
