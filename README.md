# M.A.R.K.E.T AI Platform (v3.5.0)

> **M.A.R.K.E.T**: Modular Automated Response & Knowledge Engine for Trade  
> Autonomous E-Commerce, Multi-Channel Commerce & CRM Engine with Visual Scratch Workflow Studio and DevOps Observability.

---

## 📖 English Documentation

### Overview

**M.A.R.K.E.T** is an open-source, offline-first AI infrastructure designed to automate e-commerce operations, customer communications (WhatsApp, Facebook Messenger, TikTok), inventory querying, and visual workflow automation.

The platform runs completely on local hardware (Ollama / Llama.cpp) or connects seamlessly to high-speed cloud providers (Google Gemini, Groq, OpenAI, DeepSeek).

---

### Core Capabilities in v3.5.0

1. **Scratch Visual Workflow Studio (Node & Block Architecture)**
   - Drag-and-drop conversational block editor inspired by Scratch 3.0.
   - Live Python code generation directly from visual event trees.
   - Built-in AI Coder assistance (Qwen 2.5 Coder) for generating custom logic.

2. **Backend Mission Control & Observability Dashboard**
   - Real-time diagnostics for CPU, Memory, Active Connections, and Storage.
   - Instant WhatsApp QR Code generator with live countdown and fallback pairing engine.
   - Direct IDE integration links (`vscode://`) for instant file editing (`config.json`, `products.xlsx`, `plugins/`, `bin/`).

3. **Multi-Channel Integrations**
   - **WhatsApp**: Seamless OpenWA integration with on-screen QR canvas pairing, webhook support, and automated purchase confirmations.
   - **Facebook Messenger & Comments**: Automated public comment replies and private inbox routing.
   - **TikTok & Vision Barcode**: Automated webhook listeners and barcode/QR catalog lookup.

4. **Multi-AI Fallback & Zero-Hallucination Grounding**
   - **Level 1**: Local Models (Qwen 2.5, Llama 3.2 via Ollama or custom endpoint).
   - **Level 2**: High-Speed Cloud APIs (Google Gemini 2.5 Flash, Groq, OpenAI, DeepSeek).
   - **Level 3**: Deterministic Rule Engine ensuring continuous 99.9% uptime.
   - Strict data grounding against Excel (`products.xlsx`) and SQLite databases to prevent hallucination.

5. **Production IT & DevOps Suite**
   - Complete containerization via Docker & `docker-compose.yml`.
   - Native Linux Systemd service unit (`market-ai.service`).
   - Nginx Reverse Proxy template with SSL and WebSocket support (`nginx.conf.example`).
   - Automated deployment and start scripts (`start.sh`, `deploy.sh`).
   - Comprehensive deployment guide ([`IT_DEPLOYMENT_GUIDE.md`](file:///home/hema/Downloads/files%281%29/M.A.R.K.E.T/IT_DEPLOYMENT_GUIDE.md)).

---

### Quick Start

```bash
# Clone the repository
git clone https://github.com/ielfeqi-rgb/M.A.R.K.E.T.git
cd M.A.R.K.E.T

# Method 1: Using Start Script (Native venv)
chmod +x start.sh
./start.sh

# Method 2: Using Docker Compose
docker-compose up -d --build
```

Access the Mission Control Dashboard at `http://localhost:8000`  
Explore the Interactive API Documentation at `http://localhost:8000/docs`

---

## 📜 التوثيق باللغة العربية (Arabic Documentation)

### نظرة عامة
منصة **M.A.R.K.E.T (v3.5.0)** هي بنية تحتية برمجية مفتوحة المصدر لإدارة التجارة الإلكترونية، وأتمتة خدمة العملاء عبر قنوات البيع الرقمية (واتساب، فيسبوك، تيك توك)، وإدارة المخزون والتطوير المرئي للإضافات عبر استوديو بلوكات سكراتش.

### أبرز المميزات في الإصدار v3.5.0:
1. **استوديو سكراتش للبرمجة المرئية**: تصميم تدفقات المحادثات بالسحب والإفلات وتوليد كود Python حقيقي مع دعم المبرمج الذكي (Qwen 2.5 Coder).
2. **لوحة التحكم والمراقبة التشخيصية**: فحص حي للموارد، استخراج QR الواتساب المباشر، وروابط تشغيل الملفات من محررك البرمجي.
3. **جاهزية الـ IT والنشر الفوري**: دعم دوكر، Systemd، Nginx، وسكريبتات نشر مؤتمتة بضغطة زر واحدة.

---

### 📜 License & Terms of Use

Distributed under the **PolyForm NonCommercial License 1.0.0 (CC BY-NC-SA 4.0)**.  
Free for personal, educational, and open-source non-profit use.

*Copyright (c) 2026 M.A.R.K.E.T AI Systems.*
