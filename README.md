<p align="right">
  <a href="./README_ar.md">العربية</a> | <a href="./README.md">English</a>
</p>

# M.A.R.K.E.T

**Modular Automated Response & Knowledge Engine for Trade**

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Release](https://img.shields.io/github/v/release/ielfeqi-rgb/M.A.R.K.E.T?style=flat-square&color=orange)](https://github.com/ielfeqi-rgb/M.A.R.K.E.T/releases)
[![License](https://img.shields.io/badge/License-PolyForm%20NonCommercial-green?style=flat-square)](./LICENSE)

An extensible, self-hosted commerce automation server and visual workflow studio for multi-channel sales (WhatsApp, Facebook Messenger, TikTok) and inventory management.

---

## Architecture Overview

M.A.R.K.E.T combines an asynchronous FastAPI backend with a visual Scratch-like workflow engine to let teams automate customer support, stock queries, and order routing with minimal setup.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        M.A.R.K.E.T Architecture                        │
├──────────────────────────┬─────────────────────────────────────────────┤
│ Frontend Studio          │ Visual Block Editor (Scratch paradigm)      │
│ Backend Server           │ FastAPI (ASGI / Python 3.12+)               │
│ Messaging Gateways       │ WhatsApp (OpenWA), Meta Messenger, Webhooks │
│ Data Grounding           │ Excel (openpyxl) & SQLite (market.db)       │
│ AI Inference Layer       │ Local (Llama.cpp / Ollama) + Cloud API      │
│ Deployment Targets       │ Docker, Docker Compose, Linux Systemd       │
└──────────────────────────┴─────────────────────────────────────────────┘
```

---

## Core Components

- **Visual Workflow Builder**: Build conversation trees and logic flows visually using drag-and-drop event blocks, which compile directly into executable Python code.
- **Multi-Channel Adapters**:
  - **WhatsApp**: OpenWA gateway integration with instant QR canvas pairing and automated order confirmations.
  - **Facebook & Instagram**: Messenger webhook listener, auto-reply to public comments and direct inbox messaging.
  - **TikTok & Webhooks**: Inbound payload parser for order notifications.
- **Inventory & Grounding Engine**: Real-time product search with Arabic natural-language token matching against `products.xlsx` and SQLite databases to prevent model hallucination.
- **Inference Pipeline**: Configurable fallback chain prioritizing local offline models (`Qwen 2.5`, `Llama 3.2`) with optional routing to Google Gemini, Groq, or OpenAI.
- **DevOps & Observability**: Real-time CPU, RAM, active connections, and latency metrics with pre-configured Docker Compose, Systemd unit, and Nginx reverse proxy templates.

---

## Getting Started

### Prerequisites

- Python 3.10+ (Python 3.12 recommended)
- `pip` and `venv`
- Docker & Docker Compose (optional, for containerized deployment)

### Quick Start (Local)

1. Clone the repository:
   ```bash
   git clone https://github.com/ielfeqi-rgb/M.A.R.K.E.T.git
   cd M.A.R.K.E.T
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env to add your preferred API keys and settings
   ```

3. Run the automated startup script:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

4. Open the dashboard in your browser:
   - **Mission Control & Diagnostics**: [http://localhost:8000](http://localhost:8000)
   - **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Production Deployment

### Option A: Docker Compose (Recommended)

```bash
cp .env.example .env
docker-compose up -d --build
```

### Option B: Linux Systemd (VPS / Bare-Metal)

```bash
sudo ./deploy.sh
```

For detailed production instructions including Nginx reverse proxy configuration and SSL setup with Let's Encrypt, see [`IT_DEPLOYMENT_GUIDE.md`](./IT_DEPLOYMENT_GUIDE.md).

---

## Project Structure

```
M.A.R.K.E.T/
├── main.py                 # FastAPI application entrypoint & REST routers
├── scratch_engine.py       # Visual block-to-code compiler engine
├── bot_logic.py            # Customer support dialogue logic and routing
├── ai_provider.py          # Unified client for local and cloud AI providers
├── excel_helper.py         # In-memory spreadsheet indexing and fuzzy search
├── plugin_manager.py       # Dynamic plugin loader and runtime registry
├── config.json             # Runtime configuration file
├── products.xlsx           # Product catalog dataset
├── plugins/                # Modular channel adapters and extensions
│   ├── whatsapp_openwa/    # WhatsApp integration
│   ├── facebook_messenger/ # Meta Messenger integration
│   ├── tiktok_webhook/     # TikTok webhook handler
│   └── qr_excel_lookup/    # QR barcode inventory lookup
├── Dockerfile              # Production container build
├── docker-compose.yml      # Multi-service stack (Core + WhatsApp Gateway)
├── market-ai.service       # Linux Systemd unit template
├── nginx.conf.example      # Nginx reverse proxy template
├── start.sh                # Local launch script
├── deploy.sh               # Production deployment script
└── static/                 # Dashboard and studio web assets
```

---

## Open Source Credits & Acknowledgments

This project is built on the shoulders of giants. We gratefully acknowledge and credit the creators and maintainers of the following open-source technologies:

| Project | Author / Organization | Description / Role |
| :--- | :--- | :--- |
| **[FastAPI](https://fastapi.tiangolo.com/)** | Sebastián Ramírez ([@tiangolo](https://github.com/tiangolo)) | High-performance asynchronous web framework |
| **[Uvicorn](https://www.uvicorn.org/)** | Encode OSS | Lightning-fast ASGI web server |
| **[Scratch](https://scratch.mit.edu/)** | MIT Media Lab | Visual block-based programming paradigm inspiration |
| **[OpenWA / WPPConnect](https://github.com/open-wa/wa-automate-nodejs)** | Mohammed Shah & Community | Headless WhatsApp Web automation gateway |
| **[llama.cpp](https://github.com/ggerganov/llama.cpp)** | Georgi Gerganov & Contributors | Efficient local LLM inference in C/C++ |
| **[Qwen Models](https://github.com/QwenLM/Qwen2.5)** | Alibaba Cloud / Qwen Team | Qwen 2.5 & Qwen 2.5 Coder foundation models |
| **[Llama](https://github.com/meta-llama/llama3)** | Meta AI | Llama 3 open foundation models |
| **[openpyxl](https://openpyxl.readthedocs.io/)** | Eric Gazoni, Charlie Clark | Pure-Python Excel spreadsheet manipulation |
| **[Pydantic](https://docs.pydantic.dev/)** | Samuel Colvin & Contributors | Data validation and settings management |
| **[Lucide Icons](https://lucide.dev/)** | Lucide Project | Clean and consistent UI iconography |
| **[Tailwind CSS](https://tailwindcss.com/)** | Tailwind Labs | Utility-first CSS framework |

---

## License

This project is licensed under the **PolyForm NonCommercial License 1.0.0 (CC BY-NC-SA 4.0)**.  
Free for personal, educational, and open-source non-commercial use.

For commercial licenses, please contact the project owner.
