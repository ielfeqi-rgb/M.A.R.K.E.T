<p align="right">
  <a href="./README_ar.md">العربية</a> | <a href="./README.md">English</a>
</p>

<p align="center">
  <h1 align="center">M.A.R.K.E.T AI (v4.0.0 Enterprise)</h1>
  <p align="center">
    <strong>Modular Automated Response & Knowledge Engine for Trade</strong><br/>
    <em>Next-Generation Visual DAG Node Studio, Multi-Model Local AI Orchestration & Real-Time Commerce Automation</em>
  </p>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+"/></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/></a>
  <a href="https://www.sqlite.org/"><img src="https://img.shields.io/badge/SQLite-WAL%20Engine-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite WAL"/></a>
  <a href="https://github.com/QwenLM/Qwen2.5"><img src="https://img.shields.io/badge/AI%20Synthesizer-Qwen%202.5%20Coder-6366F1?style=for-the-badge&logo=openai&logoColor=white" alt="Qwen 2.5 Coder"/></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-Production%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/Release-v4.0.0%20Enterprise-10B981?style=for-the-badge" alt="Release v4.0.0"/></a>
</p>

---

## 🌟 Visual Workflow & DAG Node Studio

<p align="center">
  <img src="./docs/images/visual-node-graph.png" alt="M.A.R.K.E.T v4.0.0 Visual Node Graph Studio" width="900" style="border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);"/>
</p>

**M.A.R.K.E.T v4.0.0** is an enterprise-grade, self-hosted commerce automation platform that bridges visual flow orchestration with autonomous code synthesis. Teams can design, trace, and execute complex multi-step dialogue trees, custom business logic, and automated checkout funnels using an infinite 2D DAG canvas that compiles directly into high-performance async Python code.

---

## ⚡ Key Highlights (v4.0.0 Enterprise)

- **🎨 Infinite 2D Visual DAG Canvas**: Node-based flow designer with magnetic pin snapping, live cubic bezier signal rendering, and real-time step latency profiling.
- **🧠 Autonomous Code Synthesis (Qwen 2.5 Coder)**: Dynamic AI synthesizer that transforms custom requirements (e.g., promo codes, external Excel parsers, SQL matchers) into interactive nodes and executable Python backend modules.
- **⚡ Dual-Model Concurrency Engine**: Independent concurrent inference streams — **Model 1** dedicated to real-time coding and schema generation, **Model 2** dedicated to customer care and omni-channel messaging.
- **💾 ACID SQLite Write-Ahead Logging (WAL)**: High-concurrency zero-hallucination inventory storage with sub-millisecond query execution and automated Excel (`products.xlsx`) bidirectional synchronization.
- **📱 Omni-Channel Gateway Hub**: Native WhatsApp OpenWA integration with instant QR-canvas pairing, Facebook Messenger webhook dispatch, and TikTok commerce hooks.
- **🛠️ Integrated Live Inspector & Telemetry Suite**: Real-time DAG execution tracer, token profiler (`tokens/sec`), SQL console, and concurrency burst stress tester (`P50/P95` metrics).

---

## 🏗️ Architecture & Component Topology

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    M.A.R.K.E.T v4.0.0 Enterprise Core Topology                   │
├──────────────────────────┬───────────────────────────────────────────────────────┤
│ Visual Node Studio       │ React 19 + Tailwind CSS + Lucide 2D Bezier Canvas     │
│ Asynchronous Engine      │ FastAPI (ASGI / Python 3.12+) with Connection Pooling │
│ AI Code Synthesizer      │ Qwen 2.5 Coder (0.5B / 1.5B / 3B) via Ollama & Llama  │
│ Customer Care AI         │ Local Llama-Server / Gemini 2.5 Flash / Groq Cloud    │
│ Grounding & Storage      │ SQLite 3.45+ in WAL Mode + InMemory Excel Cache       │
│ Messaging Adapters       │ WhatsApp (OpenWA), Meta Graph API, Custom Webhooks    │
│ Telemetry & DevTools     │ In-Memory Broadcast Queue, P50/P95 Latency Profiler   │
│ Production Infrastructure│ Docker, Docker Compose, Nginx Reverse Proxy, Systemd  │
└──────────────────────────┴───────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **Node.js 20+** (Optional for frontend development)
- **Docker & Docker Compose** (Optional for container deployment)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/ielfeqi-rgb/M.A.R.K.E.T.git
cd M.A.R.K.E.T

# Copy environment configuration
cp .env.example .env

# Run the automated launch script
chmod +x start.sh
./start.sh
```

### 3. Open the Unified Mission Control
- **Unified Web Platform**: [http://localhost:8000](http://localhost:8000)
- **Interactive REST API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI JSON Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 🛠️ Unified Platform Modules

| Module | Description | Access |
| :--- | :--- | :--- |
| **📊 Mission Control & Telemetry** | Hardware gauges, CPU/RAM utilization, active LLM model monitoring, live logs. | `Sidebar -> لوحة القيادة` |
| **🧩 Visual Node & DAG Studio** | Infinite 2D canvas, custom node architect, live pulse simulator, plugin exporter. | `Sidebar -> استوديو العقد` |
| **🔬 DevTools & Inspector Suite** | Step-by-step DAG tracer, LLM token profiler, SQLite WAL console, stress tester. | `Sidebar -> منصة الفحص` |
| **📦 Inventory & Grounding Engine** | Real-time SQL product catalog, stock tracking, instant Excel reload. | `Sidebar -> المخزن وقاعدة البيانات` |
| **📱 WhatsApp Gateway (OpenWA)** | Web-based QR scanner, connection status, direct message testing sandbox. | `Sidebar -> بوابة واتساب` |
| **⚙️ System & AI Settings** | AI Provider switcher (Gemini, Groq, Llama, Ollama), API keys, grounding prompts. | `Sidebar -> إعدادات النظام` |

---

## 🐳 Containerized Production Deployment

Deploy the full stack (Core Server + WhatsApp Gateway + SQLite Storage) using Docker Compose:

```bash
# Start all services in daemon mode
docker-compose up -d --build

# View real-time container logs
docker-compose logs -f
```

---

## 📂 Repository Structure

```
M.A.R.K.E.T/
├── main.py                 # FastAPI application entrypoint & API routers
├── database.py             # SQLite WAL enterprise storage engine
├── scratch_engine.py       # DAG compiler & Python code generation engine
├── bot_logic.py            # Natural dialogue management & SQL grounding
├── ai_provider.py          # Multi-model LLM provider manager & fallback chain
├── hardware_detector.py    # Hardware profiling & model compatibility matrix
├── llamacpp_manager.py     # Local llama-server lifecycle manager
├── excel_helper.py         # In-memory spreadsheet indexer
├── plugin_manager.py       # Modular plugin lifecycle & route registry
├── config.json             # Runtime environment configuration
├── products.xlsx           # Catalog spreadsheet dataset
├── market_edge.db          # ACID SQLite Write-Ahead Log database
├── plugins/                # Modular channel adapters & synthesized extensions
│   ├── whatsapp_openwa/    # WhatsApp gateway adapter
│   ├── facebook_messenger/ # Meta Messenger adapter
│   ├── tiktok_webhook/     # TikTok shop webhook adapter
│   └── custom_blocks.json  # Synthesized dynamic node schemas
├── docs/                   # Documentation & high-resolution media
│   └── images/             # Architecture screenshots & workflow diagrams
├── Dockerfile              # Multi-stage production container definition
├── docker-compose.yml      # Orchestration stack definition
├── start.sh                # Local daemon launch script
└── static/                 # Production compiled single-page web application
```

---

## 🤝 Open Source Acknowledgments

We gratefully acknowledge the core open-source technologies powering M.A.R.K.E.T v4.0.0:

- **[FastAPI](https://fastapi.tiangolo.com/)** by Sebastián Ramírez ([@tiangolo](https://github.com/tiangolo)) — High-performance async web framework.
- **[Uvicorn](https://www.uvicorn.org/)** by Encode OSS — Lightning-fast ASGI web server.
- **[Qwen Models](https://github.com/QwenLM/Qwen2.5)** by Alibaba Cloud / Qwen Team — Foundation models for code synthesis and natural reasoning.
- **[llama.cpp](https://github.com/ggerganov/llama.cpp)** by Georgi Gerganov — High-efficiency local inference in C/C++.
- **[OpenWA / WPPConnect](https://github.com/open-wa/wa-automate-nodejs)** — Headless WhatsApp Web automation gateway.
- **[SQLite](https://www.sqlite.org/)** by D. Richard Hipp — ACID Write-Ahead Logging database engine.
- **[Lucide](https://lucide.dev/)** — UI iconography.
- **[Tailwind CSS](https://tailwindcss.com/)** by Tailwind Labs — Utility-first styling framework.

---

## 📄 License

This project is released under the **PolyForm NonCommercial License 1.0.0 (CC BY-NC-SA 4.0)**.  
Free for personal, educational, and open-source non-commercial use.
