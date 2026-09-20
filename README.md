<p align="right">
  <a href="./README_ar.md">العربية</a> | <a href="./README.md">English</a>
</p>

<p align="center">
  <h1 align="center">M.A.R.K.E.T Enterprise Platform (v4.0.2)</h1>
  <p align="center">
    <strong>Modular Automated Response & Knowledge Engine for Trade</strong><br/>
    <em>Enterprise Multi-Role Orchestration, Asynchronous Session Queue, CRM Composite UID Engine, Meta Graph API & Standalone Local LLM Stack</em>
  </p>
</p>

<p align="center">
  <a href="https://github.com/ielfeqi-rgb/M.A.R.K.E.T/stargazers"><img src="https://img.shields.io/github/stars/ielfeqi-rgb/M.A.R.K.E.T?style=for-the-badge&logo=github&color=blue" alt="GitHub Stars"/></a>
  <a href="https://github.com/ielfeqi-rgb/M.A.R.K.E.T/network/members"><img src="https://img.shields.io/github/forks/ielfeqi-rgb/M.A.R.K.E.T?style=for-the-badge&logo=github&color=blue" alt="GitHub Forks"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+"/></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/></a>
  <a href="https://www.sqlite.org/"><img src="https://img.shields.io/badge/SQLite-WAL%20Engine-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite WAL"/></a>
  <a href="https://github.com/QwenLM/Qwen2.5"><img src="https://img.shields.io/badge/AI%20Synthesizer-Qwen%202.5%20Coder-6366F1?style=for-the-badge&logo=openai&logoColor=white" alt="Qwen 2.5 Coder"/></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-Production%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/Release-v4.0.2%20Enterprise-10B981?style=for-the-badge" alt="Release v4.0.2"/></a>
</p>

---

## Architecture Overview

**M.A.R.K.E.T v4.0.2** is an enterprise-grade, self-hosted commerce automation platform that combines multi-channel customer communication, role-based access control (RBAC), customer relationship management (CRM) composite identity persistence, automated request queue scheduling, and local/cloud large language model orchestration into a unified, zero-dependency Python service.

---

## Core Capabilities (v4.0.2 Enterprise)

- **Role-Based Access Control (RBAC)**: Secure multi-tier authentication engine featuring PBKDF2 password hashing (100,000 iterations), session token lifecycle management, and discrete functional permission enforcement across Executive Admin, Customer Support, IT Systems, Sales, and Operations.
- **Customer Support Handover Center**: Centralized ticket handover management allowing human support agents to exclusively claim active customer conversations, suspend automated AI replies, deliver live WhatsApp responses, and reinstate automated routines upon ticket resolution.
- **Composite UID & CRM Profile Engine**: Persistent customer identification format `[PLATFORM]_[PHONE]_[INITIAL_CONTACT_TIMESTAMP]` with immutable database registration and automated tier classification (VIP, Returning, Lead, New).
- **Time & Delay Task Scheduler**: Autonomous background daemon executing long-term scheduled actions (e.g., 90-day promotional voucher dispatch, follow-up notifications) with persistent SQLite WAL state preservation across system restarts.
- **Meta Integration Gateway**: Dual-channel Meta integration featuring Meta Graph API v19.0 for post publishing and secure Webhook endpoints for real-time comment and interaction ingestion.
- **Asynchronous Request Queue & Session Sandbox Isolation**: Memory-level per-session locking mechanism preventing conversation crosstalk and race conditions, paired with multi-worker request queues and upstream gatekeeper input validation.
- **Zero-NPM Standalone Deployment**: Production-ready static web application bundled directly into the FastAPI backend, serving the entire interface, API, and background workers on a single unified port (8000) without Node.js runtime dependencies.

---

## System Architecture Topology

```
+----------------------------------------------------------------------------------+
|                    M.A.R.K.E.T v4.0.2 Enterprise Core Topology                   |
+--------------------------+-------------------------------------------------------+
| User Interface Layer     | Pre-compiled Single Page App served by FastAPI (:8000)|
| Authentication & RBAC    | PBKDF2-HMAC-SHA256 Token Auth with Fine-Grained Perms |
| Concurrency & Isolation  | Per-Session Memory Locking + Async Multi-Worker Queue |
| Customer Support Center  | Exclusive Ticket Claiming + Live Channel Dispatch     |
| CRM Identity Engine      | Immutable Composite UID + Dynamic Account Tiering     |
| Time & Delay Engine      | SQLite WAL Scheduled Trigger Daemon (Periodic Poll)   |
| Meta & Social Gateway    | Meta Graph API v19.0 Publishing + Webhook Ingest      |
| Local LLM Core           | llama-server C++ (:8081) / Ollama / Groq / Gemini     |
| Grounding & Storage      | ACID SQLite 3.45+ (WAL Mode) + Excel Synchronizer     |
+--------------------------+-------------------------------------------------------+
```

---

## Quick Start

### 1. Requirements
- Python 3.10+ (Python 3.12 recommended)
- SQLite 3.35+
- (Optional) Docker & Docker Compose for containerized environments

### 2. Standalone Launch

```bash
# Clone the repository
git clone https://github.com/ielfeqi-rgb/M.A.R.K.E.T.git
cd M.A.R.K.E.T

# Install dependencies
pip install -r requirements.txt

# Start the unified enterprise platform
python3 main.py
```

### 3. Access Mission Control
- Unified Enterprise Console: http://localhost:8000
- REST API Documentation (Swagger): http://localhost:8000/docs
- OpenAPI JSON Specification: http://localhost:8000/openapi.json

---

## Default Administrative Accounts

| Role | Username | Default Password | Target Scope |
| :--- | :--- | :--- | :--- |
| **Executive Admin** | `admin` | `admin123` | Full system access, users, settings, and telemetry |
| **Customer Support** | `cs1` | `cs123` | Support Center, chat dispatch, order assistance |
| **IT Systems** | `it_admin` | `it123` | Meta hub, scheduler, LLM engines, and diagnostics |
| **Sales Representative** | `sales1` | `sales123` | Catalog management, order tracking, and lead CRM |

---

## Unified Modules

| Module | Functional Scope | Route |
| :--- | :--- | :--- |
| **Operational Telemetry** | CPU/RAM hardware utilization, LLM health, system event logging | `/` -> Dashboard |
| **Support Center** | Ticket queue, exclusive handover, canned corporate responses | `/` -> Support Center |
| **User & RBAC Manager** | Account provisioning, role assignments, functional permissions | `/` -> Users & RBAC |
| **Flow Studio** | Visual DAG canvas, Qwen 2.5 Coder card compilation | `/` -> Flow Studio |
| **Diagnostic Suite** | Trace inspection, SQL console, token latency metrics | `/` -> DevTools |
| **Inventory Engine** | SQLite WAL stock catalog, bidirectional Excel synchronization | `/` -> Inventory |
| **System Settings** | Meta Graph API/Webhook setup, time scheduler, LLM providers | `/` -> Settings |
| **Operational Guides** | Standard operating procedures and interactive support assistant | `/` -> Operational Guide |

---

## Repository Structure

```
M.A.R.K.E.T/
|-- main.py                 # FastAPI core application, routers & standalone static server
|-- database.py             # SQLite WAL storage engine with RBAC, CRM, & Scheduler schemas
|-- auth.py                 # Authentication, PBKDF2 password hashing & RBAC permission matrix
|-- time_scheduler.py       # Asynchronous delay execution daemon & trigger worker
|-- meta_integration.py     # Meta Graph API v19.0 client & Webhook event processor
|-- request_queue.py        # Asynchronous multi-worker request queue with latency profiling
|-- request_validator.py    # Gatekeeper validation filter for inbound payload sanitization
|-- scratch_engine.py       # Visual card-to-code compiler & Python synthesizer
|-- bot_logic.py            # Dialogue management & zero-hallucination SQL grounding
|-- ai_provider.py          # LLM provider manager (Local llama-server, Gemini, Groq)
|-- hardware_detector.py    # Hardware profiling & model tier compatibility detector
|-- llamacpp_manager.py     # Local llama-server lifecycle manager
|-- excel_helper.py         # In-memory spreadsheet parser
|-- plugin_manager.py       # Modular plugin lifecycle & route registry
|-- config.json             # Runtime configuration file
|-- products.xlsx           # Catalog spreadsheet dataset
|-- market_edge.db          # ACID SQLite Write-Ahead Log database
|-- plugins/                # Modular channel adapters & synthesized extensions
|-- static/                 # Pre-compiled standalone single-page application assets
|-- Dockerfile              # Production container definition
`-- docker-compose.yml      # Multi-service stack orchestration definition
```

---

## License

This project is released under the **PolyForm NonCommercial License 1.0.0 (CC BY-NC-SA 4.0)**.  
Free for personal, educational, and open-source non-commercial deployment.
