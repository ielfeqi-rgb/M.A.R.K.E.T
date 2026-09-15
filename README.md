# 🚀 M.A.R.K.E.T AI Platform (v2.0 — OmniContext Engine)

> **M.A.R.K.E.T**: **M**ulti-AI **A**utomated **R**esponse & **K**nowledge **E**ngine for **T**rade  
> *Official Open-Source Documentation for M.A.R.K.E.T AI — Autonomous E-Commerce & Customer Service Engine powered by OmniContext AI v2.0*

---

## 📖 English Documentation (Primary)

### 🌟 What is M.A.R.K.E.T AI?

**M.A.R.K.E.T** (**M**ulti-AI **A**utomated **R**esponse & **K**nowledge **E**ngine for **T**rade) is an open-source, privacy-first, offline-capable AI infrastructure engineered to automate e-commerce customer service, Meta Facebook Messenger DMs, Feed comment auto-replies, Excel inventory lookups, QR code scanning, and dynamic Python AI plugin extensions.

Powered by the **OmniContext AI 2.0 Core**, M.A.R.K.E.T runs 100% locally on your hardware via `llama.cpp` / `llama-server` (or Ollama), eliminating recurring monthly cloud API costs while protecting customer data privacy.

---

### ✨ Key Features & Capabilities

1. **Multi-AI Fallback Chain (Offline-First Guarantee)**:
   - **Priority 1**: Local `llama-server` / `llamacpp` binary (Qwen 2.5 1.5B / Llama 3.2 GGUF models on port 8081).
   - **Priority 2**: Local Ollama (`http://localhost:11434`).
   - **Priority 3**: High-Speed Cloud APIs (Google Gemini 2.5 Flash, Groq Llama 3.3 70B, OpenAI GPT-4o Mini, DeepSeek Chat).
   - **Fallback**: Intelligent Rule-Based Engine ensuring 99.9% uptime with zero customer drop-off.

2. **Dynamic Python Plugin System (`plugins/`)**:
   - Single-file `.py` plugins dynamically loaded at runtime without restarting the server.
   - **Local AI Plugin Generator (`/api/plugins/generate`)**: Prompts local LLMs (Qwen 2.5) to write valid Python plugins on demand.
   - **Dynamic UI Snippet Injection (`get_ui_snippet`)**: Plugins can dynamically inject custom HTML/CSS elements, badges, and widgets into the dashboard topbar.
   - Lifecycle Hooks: `on_message_received`, `on_reply_generated`, `on_purchase_detected`, `get_ui_snippet`.

3. **Meta Facebook Messenger & Feed Integration**:
   - **Messenger DMs**: Automatic friendly Egyptian Arabic customer support & sales agent dialogues.
   - **Feed Comments**: Automatic public comment replies + private inbox message containing pricing and details.
   - **HMAC & Verify Token Security**: Built-in Meta developer Webhook verification.

4. **Excel Inventory & Vision Engine**:
   - **openpyxl Native Engine**: Fast product indexing and CRUD operations (`products.xlsx`).
   - **AI Product Code Inference**: Infers product codes from customer natural language queries (e.g., "red shirt size XL" -> `txlr`).
   - **QR Code Vision Scanner**: OpenCV scanner reads QR code images sent in customer messages to look up stock automatically.

5. **M.A.R.K.E.T Dashboard UI**:
   - Glassmorphism Responsive UI with Sidebar Navigation.
   - Dual Theme Support (Light & Dark mode).
   - Live SSE Terminal & Real-Time Tokenization Metrics (`Prompt Chars, Tokens, Response Tokens, Latency ms, Speed tok/s`).
   - Ngrok Webhook Tunnel & Complete Server OFF Power Control.

---

### 📁 Project Architecture

```
omnicontext_v2/
├── main.py              # FastAPI Web Server, Webhooks & REST Endpoints
├── plugin_manager.py    # Dynamic Python Plugin Manager & UI Injector
├── llamacpp_manager.py  # Local llama-server Process Supervisor
├── bot_logic.py         # Customer Service Dialog Engine & Context Cache
├── ai_provider.py       # Multi-AI Fallback Chain & Tokenizer Logger
├── hardware_detector.py # Hardware Spec Analyzer (RAM & CPU Cores)
├── excel_helper.py      # openpyxl Inventory Database Engine
├── http_client.py       # Connection Pooling & Async HTTP Client
├── qr_detector.py       # OpenCV Image QR Code Reader
├── settings.py          # Environment Variables & Pydantic Config
├── config.json          # Live Dashboard Config Storage
├── products.xlsx        # Default Excel Inventory File
├── plugins/             # Dynamic Plugin Directory
│   ├── chat_archiver_upsell.py  # Archiver & Upsell Plugin
│   ├── cute_dashboard_icon.py   # Cute AI Badge UI Plugin
│   └── ai_login__sessio.py      # Login & Session Manager Plugin
└── static/              # Dashboard Frontend Files
    ├── index.html       # Single Page Application Layout
    ├── style.css        # Responsive Glassmorphism Styling
    └── app.js           # Interactive UI Controller & SSE Log Receiver
```

---

### ⚙️ Quick Start & Installation

```bash
# 1. Navigate to directory
cd omnicontext_v2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch M.A.R.K.E.T AI Server
python main.py
```

Access the Dashboard UI at `http://localhost:8000`

---

### 📜 License & Terms of Use

This project is released under the **Non-Commercial Public License (PolyForm NonCommercial 1.0.0 / CC BY-NC-SA 4.0)**:

- **Free for Personal, Educational, and Non-Profit Use**: Individuals, students, researchers, and open-source developers can freely use, modify, and distribute this software for personal or non-profit purposes.
- **Commercial & Corporate Use Requires Permission**: Commercial businesses, for-profit entities, or individuals utilizing this software for commercial gain must obtain an explicit commercial license from the project owner.

*Copyright (c) 2026 M.A.R.K.E.T AI Systems (OmniContext Engine).*

---

## 📜 التوثيق باللغة العربية (Arabic Summary)

### 🎯 ما هي منصة M.A.R.K.E.T AI؟

اسم المنصة **M.A.R.K.E.T** هو اختصار لـ:  
**M**ulti-AI **A**utomated **R**esponse & **K**nowledge **E**ngine for **T**rade  
*(محرك الذكاء الاصطناعي والاستجابة الاستعلامية المؤتمتة للتجارة)*

منصة **M.A.R.K.E.T AI 2.0** هي بنية تحتية مجانية ومفتوحة المصدر لأتمتة خدمة العملاء والمبيعات للمتاجر الإلكترونية وصفحات التواصل الاجتماعي دون تكاليف شهرية متكررة وبخصوصية تامة للبيانات عبر التشغيل المحلي التام.

### 🌟 أبرز المميزات
- **سلسلة محركات الذكاء الاصطناعي المتعاقبة**: تشغيل محلي عبر `llama-server` أو Ollama مع تحول آلي مرن إلى Gemini أو Groq أو OpenAI.
- **نظام الإضافات الديناميكي**: إنشاء وتفعيل إضافات Python بالذكاء الاصطناعي المحلي وزراعة عناصر الواجهة (UI Snippets) فورياً.
- **ربط فيسبوك والتعليقات**: رد آلي في الماسنجر والتعليقات والإنبوكس.
- **شيت الإكسيل والـ QR**: فرز مخزون المنتجات وقراءة أكواد الـ QR من صور العملاء.

---

> **M.A.R.K.E.T Systems Documentation © 2026**  
> *OmniContext AI Core Engineering Team*
