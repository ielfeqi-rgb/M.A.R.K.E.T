# M.A.R.K.E.T AI (OmniContext Engine v2.0) - TODO & Project Roadmap

## 📅 Completed Today (Summary of Accomplishments)
- [x] **Dynamic Python Plugin Manager (`plugin_manager.py`)**: Built dynamic `.py` plugin loader, state toggle manager, and hook dispatchers (`on_message_received`, `on_reply_generated`, `on_purchase_detected`).
- [x] **AI Plugin Generator Endpoint (`/api/plugins/generate`)**: Enabled local LLM (Qwen 2.5 1.5B / llama-server) to generate new Python plugins based on prompt instructions.
- [x] **Dynamic UI Snippet Injection (`get_ui_snippet`)**: Equipped plugins to dynamically inject custom HTML/CSS elements (like badges and status pills) into the topbar header layout.
- [x] **Sample Plugins**:
  - `plugins/chat_archiver_upsell.py`: Archives purchase chats and generates mock upsells.
  - `plugins/cute_dashboard_icon.py`: Injects a glowing cute AI badge icon into the dashboard header.
  - `plugins/ai_login__sessio.py`: Manages user login & session authentication.
- [x] **Verbose Tokenization & Speed Stream**: Detailed live logging of prompt characters, estimated tokens, response tokens, latency (ms), and speed (tok/s).
- [x] **Server Shutdown Endpoint Fix**: Fixed `import time` NameError in `main.py` when clicking the UI OFF button.
- [x] **Repo Synchronization & Git Commit**: Clean sync between `omnicontext_v2` and `omnicontext_complete`.

---

## 📌 TODO List for Tomorrow (Next Steps & Enhancements)

### 1. 🔐 Enhanced Authentication & Dashboard Protection
- [ ] Add a lightweight JWT / Session Password protection middleware for dashboard UI tabs.
- [ ] Allow configuring admin password in settings tab.

### 2. 🔌 Additional Smart Plugins
- [ ] **Auto Discount Plugin**: Detects returning customers and offers custom discount codes automatically.
- [ ] **Order Tracking Plugin**: Searches order status by customer phone number / Messenger ID.

### 3. 📊 Dashboard Analytics & Export
- [ ] Add conversation analytics & top products chart to Dashboard tab.
- [ ] Add one-click export for archived chats to JSON / Excel.

---

*Project status: 100% stable & ready for tomorrow's development.*
