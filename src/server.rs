use crate::crm::{CrmManager, LeadRecord};
use crate::hardware::{SystemProfile, WorkloadMode};
use crate::llamacpp::{LlamaManager, LlamaServerStatus};
use crate::plugins::{PipelineResult, PluginEngine, PluginInput, PluginManifest};
use axum::{
    extract::{Path, Query, State},
    response::Html,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use tower_http::cors::CorsLayer;

#[derive(Clone)]
pub struct AppState {
    pub client: reqwest::Client,
    pub llama: Arc<LlamaManager>,
    pub plugins: Arc<Mutex<PluginEngine>>,
    pub crm: Arc<Mutex<CrmManager>>,
}

#[derive(Deserialize)]
pub struct ProfileQuery {
    pub mode: Option<String>,
}

#[derive(Serialize, Deserialize)]
pub struct StartRequest {
    pub model_filename: Option<String>,
    pub threads: Option<usize>,
    pub context_size: Option<usize>,
}

#[derive(Serialize, Deserialize)]
pub struct InstallRequest {
    pub model_url: String,
    pub model_filename: String,
    pub threads: usize,
}

#[derive(Serialize, Deserialize)]
pub struct ChatRequest {
    pub message: String,
    pub system_prompt: Option<String>,
    pub channel_plugin: Option<String>,
    pub domain_plugin: Option<String>,
    pub metadata: Option<serde_json::Value>,
}

#[derive(Serialize, Deserialize)]
pub struct ChatResponse {
    pub success: bool,
    pub reply: String,
    pub provider: String,
    pub latency_ms: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub pipeline_details: Option<PipelineResult>,
}

#[derive(Deserialize)]
pub struct TogglePluginRequest {
    pub plugin_id: String,
    pub enable: bool,
}

#[derive(Deserialize)]
pub struct TestPluginRequest {
    pub plugin_id: String,
    pub user_message: String,
    pub metadata: Option<serde_json::Value>,
}

#[derive(Deserialize)]
pub struct GenericWebhookPayload {
    pub sender_id: Option<String>,
    pub sender_name: Option<String>,
    pub message: Option<String>,
    pub phone: Option<String>,
    pub domain_plugin: Option<String>,
}

#[derive(Deserialize)]
pub struct MetaVerifyQuery {
    #[serde(rename = "hub.mode")]
    pub mode: Option<String>,
    #[serde(rename = "hub.verify_token")]
    pub verify_token: Option<String>,
    #[serde(rename = "hub.challenge")]
    pub challenge: Option<String>,
}

#[derive(Deserialize)]
pub struct UpdateLeadStatusRequest {
    pub id: String,
    pub status: String,
}

const DASHBOARD_HTML: &str = r#"<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M.A.R.K.E.T. Enterprise AI Engine & Modular Plugin Host</title>
    <style>
        :root {
            --bg: #020617;
            --surface: #0f172a;
            --border: #1e293b;
            --text: #f1f5f9;
            --muted: #94a3b8;
            --accent: #f59e0b;
            --accent-hover: #d97706;
            --accent-glow: rgba(245, 158, 11, 0.15);
            --success: #10b981;
            --danger: #ef4444;
            --info: #38bdf8;
            --purple: #a855f7;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 13px;
            padding: 20px;
            line-height: 1.6;
        }
        .container { max-width: 1040px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .logo { font-size: 17px; font-weight: bold; color: #fff; display: flex; align-items: center; gap: 10px; }
        .version-badge {
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.4);
            color: var(--accent);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        }
        .pulse { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-left: 6px; }
        .pulse-green { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .pulse-red { background: var(--danger); }
        .pulse-amber { background: var(--accent); animation: blink 1.2s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

        /* Navigation Tabs */
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; flex-wrap: wrap; }
        .tab-btn {
            background: transparent;
            color: var(--muted);
            border: 1px solid var(--border);
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 12px;
            transition: all 0.2s;
        }
        .tab-btn.active {
            background: var(--accent-glow);
            color: var(--accent);
            border-color: var(--accent);
        }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 20px;
        }
        .card-title {
            font-size: 14px;
            font-weight: bold;
            color: var(--accent);
            border-bottom: 1px solid var(--border);
            padding-bottom: 10px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
        .box {
            background: #020617;
            border: 1px solid var(--border);
            padding: 12px;
            border-radius: 6px;
        }
        .label { color: var(--muted); font-size: 11px; display: block; margin-bottom: 4px; }
        .val { font-weight: bold; color: #fff; }

        .mode-selector { display: flex; gap: 12px; margin-bottom: 16px; }
        .mode-card {
            flex: 1;
            padding: 14px;
            border-radius: 8px;
            border: 2px solid var(--border);
            background: #020617;
            cursor: pointer;
            transition: all 0.2s;
        }
        .mode-card:hover { border-color: rgba(245, 158, 11, 0.5); }
        .mode-card.selected { border-color: var(--accent); background: var(--accent-glow); }

        .btn {
            background: var(--accent);
            color: #020617;
            border: none;
            padding: 9px 18px;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            font-family: inherit;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }
        .btn:hover { background: var(--accent-hover); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-success { background: var(--success); color: #fff; }
        .btn-danger { background: var(--danger); color: #fff; }
        .btn-outline { background: transparent; color: var(--text); border: 1px solid var(--border); }
        .btn-outline:hover { border-color: var(--accent); }

        /* Installation Visual Box */
        .install-box {
            background: #020617;
            border: 1px solid rgba(245, 158, 11, 0.4);
            box-shadow: 0 0 15px rgba(245, 158, 11, 0.1);
            border-radius: 8px;
            padding: 16px;
            margin-top: 14px;
            transition: all 0.3s ease;
        }
        .progress-bar {
            width: 100%;
            height: 10px;
            background: #0f172a;
            border-radius: 5px;
            overflow: hidden;
            border: 1px solid var(--border);
            margin: 10px 0;
            position: relative;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #d97706, #f59e0b, #10b981);
            width: 0%;
            transition: width 0.4s ease-in-out;
            box-shadow: 0 0 10px var(--accent);
        }

        .log-console {
            background: #000;
            border: 1px solid var(--border);
            color: #38bdf8;
            padding: 10px;
            border-radius: 5px;
            font-size: 11px;
            max-height: 120px;
            overflow-y: auto;
            margin-top: 10px;
            white-space: pre-wrap;
        }

        .input-group { margin-bottom: 12px; }
        label { display: block; margin-bottom: 6px; color: var(--muted); font-size: 11px; }
        input[type="text"], select, textarea {
            width: 100%;
            background: #020617;
            border: 1px solid var(--border);
            padding: 9px 12px;
            color: #fff;
            font-family: inherit;
            font-size: 12px;
            border-radius: 5px;
            outline: none;
        }
        input[type="text"]:focus, select:focus, textarea:focus { border-color: var(--accent); }

        .output-box {
            background: #020617;
            border: 1px solid var(--border);
            padding: 14px;
            border-radius: 6px;
            white-space: pre-wrap;
            margin-top: 10px;
            font-family: sans-serif;
            font-size: 13px;
            line-height: 1.6;
        }

        .plugin-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
        .plugin-card {
            background: #020617;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .plugin-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        }
        .badge-channel { background: rgba(56, 189, 248, 0.2); color: var(--info); border: 1px solid var(--info); }
        .badge-domain { background: rgba(168, 85, 247, 0.2); color: var(--purple); border: 1px solid var(--purple); }

        .switch { position: relative; display: inline-block; width: 38px; height: 20px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #334155; transition: .3s; border-radius: 20px; }
        .slider:before { position: absolute; content: ""; height: 14px; width: 14px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
        input:checked + .slider { background-color: var(--success); }
        input:checked + .slider:before { transform: translateX(18px); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <span>🚀 M.A.R.K.E.T. Enterprise AI Systems</span>
                <span class="version-badge">v1.0.0 (Live Supervisor, Webhooks & CRM)</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <button class="btn btn-outline" onclick="loadAll()">تحديث حالة النظام 🔄</button>
            </div>
        </header>

        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('tab-plugins')">🔌 المحولات والإضافات</button>
            <button class="tab-btn" onclick="switchTab('tab-hardware')">⚙️ العتاد والنموذج المحلي</button>
            <button class="tab-btn" onclick="switchTab('tab-chat')">💬 منصة الاستدلال</button>
            <button class="tab-btn" onclick="switchTab('tab-webhooks')">🌐 محاكي الـ Webhooks الحية</button>
            <button class="tab-btn" onclick="switchTab('tab-crm')">📊 لوحة CRM والعملاء</button>
        </div>

        <!-- TAB 1: PLUGINS MANAGER -->
        <div id="tab-plugins" class="tab-content active">
            <section class="card">
                <div class="card-title">
                    <span>🔌 موديول الإضافات والمحولات المكتشفة (Dynamic OmniPlugin Manager)</span>
                    <button class="btn btn-outline" style="font-size: 10px; padding: 4px 8px;" onclick="reloadPlugins()">إعادة كشف القرص 🔄</button>
                </div>
                <div style="font-size: 11px; color: var(--muted); margin-bottom: 14px;">
                    الإضافات القابلة للتخصيص يتم تحميلها تلقائياً من مجلد <code>plugins/</code>. يمكنك تفعيل/تعطيل الإضافات حياً دون الحاجة لإعادة تشغيل النظام.
                </div>

                <div class="plugin-grid" id="plugins-container"></div>
            </section>

            <section class="card">
                <div class="card-title">
                    <span>🧪 وحدة اختبار الإضافات الفردية (Plugin Unit Sandbox)</span>
                </div>
                <div class="grid" style="grid-template-columns: 1fr 2fr;">
                    <div>
                        <div class="input-group">
                            <label>اختر الإضافة للاختبار:</label>
                            <select id="test-plugin-select"></select>
                        </div>
                        <div class="input-group">
                            <label>نص التجربة (User Message):</label>
                            <input type="text" id="test-msg-input" value="عندكم تيشيرت TS-102 وبكام الشحن؟">
                        </div>
                        <button class="btn" onclick="runPluginTest()">اختبار الإضافة ⚡</button>
                    </div>
                    <div>
                        <label>نتيجة المعالجة والسياق المحقون (Plugin Result):</label>
                        <div class="output-box" id="plugin-test-out" style="min-height: 120px; font-size: 11px;">في انتظار الاختبار...</div>
                    </div>
                </div>
            </section>
        </div>

        <!-- TAB 2: HARDWARE & LLAMA CONTROLLER -->
        <div id="tab-hardware" class="tab-content">
            <section class="card">
                <div class="card-title">
                    <span>[1] تخصيص وضع التشغيل وفحص العتاد</span>
                </div>
                <div class="mode-selector">
                    <div class="mode-card selected" id="card-casual" onclick="selectMode('casual_trial')">
                        <div style="font-weight: bold; font-size: 13px; color: #fff;">🟢 وضع التجربة الخفيفة (Casual Trial)</div>
                        <div style="font-size: 11px; color: var(--muted); margin-top: 4px;">استهلاك آمن للرام واستخدام نصف الأنوية للمهام اليومية.</div>
                    </div>
                    <div class="mode-card" id="card-server" onclick="selectMode('dedicated_server')">
                        <div style="font-weight: bold; font-size: 13px; color: #fff;">🔥 وضع السيرفر المخصص (100% Power)</div>
                        <div style="font-size: 11px; color: var(--muted); margin-top: 4px;">تخصيص كامل العتاد والذاكرة لتشغيل خادم مخصص.</div>
                    </div>
                </div>
                <div class="grid">
                    <div class="box"><span class="label">المعالج:</span><span class="val" id="cpu-name">--</span></div>
                    <div class="box"><span class="label">الرامات:</span><span class="val" id="ram-info">--</span></div>
                    <div class="box"><span class="label">AVX2:</span><span class="val" id="avx-info">--</span></div>
                    <div class="box"><span class="label">GPU:</span><span class="val" id="gpu-info">--</span></div>
                </div>
            </section>

            <section class="card">
                <div class="card-title">
                    <span>[2] لوحة التحكم والتحميل التفاعلي (Interactive llama.cpp Supervisor)</span>
                    <span id="server-status-pill" style="font-size: 11px;">--</span>
                </div>
                
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px;">
                    <button class="btn" id="btn-install" onclick="triggerInstall()">
                        <span>⚙️ تثبيت llama.cpp والنموذج تلقائياً</span>
                    </button>
                    <button class="btn btn-success" id="btn-start" onclick="startLlamaServer()">🚀 تشغيل الخادم المحلي</button>
                    <button class="btn btn-danger" id="btn-stop" onclick="stopLlamaServer()">🛑 إيقاف الخادم</button>
                </div>

                <!-- Live Visual Progress Box -->
                <div id="install-box" class="install-box" style="display: none;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span id="install-step-text" style="font-weight: bold; color: var(--accent); font-size: 12px;">جاري إعداد التثبيت...</span>
                        <span id="install-percent-badge" style="background: var(--accent-glow); border: 1px solid var(--accent); color: var(--accent); padding: 2px 8px; border-radius: 12px; font-weight: bold; font-size: 11px;">0%</span>
                    </div>

                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-bar-fill"></div>
                    </div>

                    <div style="font-size: 10px; color: var(--muted); margin-top: 4px;">
                        * عملية التثبيت والبناء وتنزيل الموديل تتم في الخلفية مع التحديث البصري اللحظي للحالة.
                    </div>

                    <div class="log-console" id="install-log-console">
                        [النظام]: بانتظار بدء العملية...
                    </div>
                </div>
            </section>
        </div>

        <!-- TAB 3: PIPELINE CHAT CONSOLE -->
        <div id="tab-chat" class="tab-content">
            <section class="card">
                <div class="card-title">
                    <span>💬 تجربة المحادثة ومسار الـ Pipeline المدمج</span>
                </div>

                <div class="grid" style="grid-template-columns: 1fr 1fr; margin-bottom: 12px;">
                    <div class="input-group">
                        <label>اختر محول المجال (Domain Adapter):</label>
                        <select id="chat-domain-select"><option value="">-- بدون محول مجال --</option></select>
                    </div>
                    <div class="input-group">
                        <label>اختر محول القناة (Channel Adapter):</label>
                        <select id="chat-channel-select"><option value="">-- بدون محول قناة --</option></select>
                    </div>
                </div>

                <div class="input-group">
                    <label>السؤال أو رسالة العميل التجريبية:</label>
                    <div style="display: flex; gap: 8px;">
                        <input type="text" id="pipeline-prompt" value="عندكم تيشيرت TS-102 ومقاس L بكام ومعاه خصم؟">
                        <button class="btn" onclick="sendPipelinePrompt()">إرسال عبر الـ Pipeline ⚡</button>
                    </div>
                </div>

                <div id="pipeline-res-wrapper" style="display: none; margin-top: 14px;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); margin-bottom: 4px;">
                        <span id="pipe-provider">المصدر: --</span>
                        <span id="pipe-latency" style="color: var(--accent); font-weight: bold;">--</span>
                    </div>
                    <div class="output-box" id="pipe-response-text"></div>

                    <div style="margin-top: 14px; border-top: 1px solid var(--border); padding-top: 10px;">
                        <span style="font-weight: bold; color: var(--accent); font-size: 12px;">🔍 تفاصيل السياق المحقون والـ Metadata:</span>
                        <div class="output-box" id="pipe-debug-details" style="font-size: 11px; color: var(--muted);"></div>
                    </div>
                </div>
            </section>
        </div>

        <!-- TAB 4: WEBHOOKS SIMULATOR & TESTER -->
        <div id="tab-webhooks" class="tab-content">
            <section class="card">
                <div class="card-title">
                    <span>🌐 محاكي ومستقبل الـ Webhooks الحية (Universal Webhook Receiver & Simulator)</span>
                    <span class="version-badge" style="background: rgba(16, 185, 129, 0.2); color: var(--success); border-color: var(--success);">
                        Endpoint: /api/webhooks/{channel}
                    </span>
                </div>
                <div style="font-size: 11px; color: var(--muted); margin-bottom: 14px;">
                    محاكاة واختبار استقبال إشارات الرسائل والتعليقات من المنصات الخارجية في الوقت الفعلي ومتابعة معالجتها آلياً.
                </div>

                <div class="grid" style="grid-template-columns: 1fr 1fr; margin-bottom: 12px;">
                    <div class="input-group">
                        <label>اختر القناة والمنصة (Channel):</label>
                        <select id="wh-channel-select">
                            <option value="instagram">Instagram Direct DM (/api/webhooks/instagram)</option>
                            <option value="facebook">Facebook Messenger (/api/webhooks/facebook)</option>
                            <option value="telegram">Telegram Bot (/api/webhooks/telegram)</option>
                            <option value="tiktok">TikTok Shop Webhook (/api/webhooks/tiktok)</option>
                        </select>
                    </div>
                    <div class="input-group">
                        <label>نماذج مجهزة مسبقاً للعرض المباشر (Demo Presets):</label>
                        <select id="wh-preset-select" onchange="applyWebhookPreset()">
                            <option value="custom">-- اختر نموذج العرض المباشر --</option>
                            <option value="fashion_ig">استفسار منتج TS-102 (إنستجرام DM)</option>
                            <option value="estate_tg">حساب قسط تمويل عقاري (بوت تلجرام)</option>
                            <option value="qr_tiktok">فحص كود باركود QR المخزن (تيك توك شوب)</option>
                        </select>
                    </div>
                </div>

                <div class="grid" style="grid-template-columns: 1fr 1fr; margin-bottom: 12px;">
                    <div class="input-group">
                        <label>اسم العميل (Customer Name / ID):</label>
                        <input type="text" id="wh-sender-name" value="أحمد محمود (عميل مهتم)">
                    </div>
                    <div class="input-group">
                        <label>رقم الهاتف (اختياري للاستخراج):</label>
                        <input type="text" id="wh-phone" value="01012345678">
                    </div>
                </div>

                <div class="input-group">
                    <label>نص الرسالة أو تعليق السوشيال ميديا (Incoming Webhook Message):</label>
                    <div style="display: flex; gap: 8px;">
                        <input type="text" id="wh-msg-input" value="عندكم تيشيرت TS-102 ومقاس L بكام ومعاه خصم؟ ورقمي 01012345678">
                        <button class="btn btn-success" onclick="sendWebhookSim()">إرسال Webhook حي ⚡</button>
                    </div>
                </div>

                <div id="wh-res-wrapper" style="display: none; margin-top: 14px;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); margin-bottom: 4px;">
                        <span id="wh-res-status">الحالة: --</span>
                        <span style="color: var(--success); font-weight: bold;">تم تسجيل العميل في الـ CRM تلقائياً ✅</span>
                    </div>
                    <div class="output-box" id="wh-reply-text"></div>

                    <div style="margin-top: 14px; border-top: 1px solid var(--border); padding-top: 10px;">
                        <span style="font-weight: bold; color: var(--accent); font-size: 12px;">📡 استجابة الـ Outbound Payload الرسمية للمنصة:</span>
                        <div class="output-box" id="wh-outbound-debug" style="font-size: 11px; color: var(--info);"></div>
                    </div>
                </div>
            </section>
        </div>

        <!-- TAB 5: LOCAL CRM & LEADS MANAGER -->
        <div id="tab-crm" class="tab-content">
            <section class="card">
                <div class="card-title">
                    <span>📊 إدارة سجل العملاء والطلبات المستخرجة (Local CRM & Leads Manager)</span>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-outline" style="font-size: 10px; padding: 4px 8px;" onclick="loadCrmLeads()">تحديث السجل 🔄</button>
                        <a href="/api/crm/export" target="_blank" class="btn" style="font-size: 10px; padding: 4px 8px; text-decoration: none; color: #020617;">تصدير CSV 📥</a>
                    </div>
                </div>
                <div style="font-size: 11px; color: var(--muted); margin-bottom: 14px;">
                    بيانات العملاء والطلبات المحفوظة تلقائياً بواسطة الذكاء الاصطناعي المحلي والمحولات عبر الـ Webhooks والمحادثات.
                </div>

                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: right;">
                        <thead>
                            <tr style="background: #020617; color: var(--accent); border-bottom: 1px solid var(--border);">
                                <th style="padding: 8px;">الكود والتاريخ</th>
                                <th style="padding: 8px;">العميل والقناة</th>
                                <th style="padding: 8px;">الهاتف والطلب</th>
                                <th style="padding: 8px;">الرسالة والرد الآلي</th>
                                <th style="padding: 8px;">الحالة والإجراء</th>
                            </tr>
                        </thead>
                        <tbody id="crm-table-body">
                            <tr><td colspan="5" style="padding: 12px; text-align: center; color: var(--muted);">جاري تحميل سجل العملاء...</td></tr>
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    </div>

    <script>
        let currentMode = 'casual_trial';
        let currentProfile = null;
        let allPlugins = [];
        let installLogs = [];

        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }

        function appendInstallLog(msg) {
            const time = new Date().toLocaleTimeString('ar-EG');
            const logLine = `[${time}] ${msg}`;
            if (!installLogs.includes(logLine)) {
                installLogs.push(logLine);
                const consoleElem = document.getElementById('install-log-console');
                if (consoleElem) {
                    consoleElem.innerText = installLogs.join('\n');
                    consoleElem.scrollTop = consoleElem.scrollHeight;
                }
            }
        }

        async function loadPlugins() {
            try {
                const res = await fetch('/api/plugins');
                allPlugins = await res.json();
                renderPluginsUI();
            } catch (err) {
                console.error(err);
            }
        }

        function renderPluginsUI() {
            const container = document.getElementById('plugins-container');
            const testSelect = document.getElementById('test-plugin-select');
            const domainSelect = document.getElementById('chat-domain-select');
            const channelSelect = document.getElementById('chat-channel-select');

            if (!container) return;

            container.innerHTML = allPlugins.map(p => `
                <div class="plugin-card">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <strong style="color: #fff; font-size: 13px;">${p.name}</strong>
                            <label class="switch">
                                <input type="checkbox" ${p.enabled ? 'checked' : ''} onchange="togglePlugin('${p.id}', this.checked)">
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div style="margin-bottom: 8px;">
                            <span class="plugin-badge ${p.plugin_type === 'channel' ? 'badge-channel' : 'badge-domain'}">
                                ${p.plugin_type === 'channel' ? 'محول قناة 📡' : 'محول مجال 🏢'}
                            </span>
                            <span style="font-size: 10px; color: var(--muted); margin-right: 6px;">v${p.version} • ${p.entrypoint}</span>
                        </div>
                        <div style="font-size: 11px; color: #cbd5e1; line-height: 1.4;">${p.description}</div>
                    </div>
                </div>
            `).join('');

            testSelect.innerHTML = allPlugins.map(p => `<option value="${p.id}">${p.name} (${p.id})</option>`).join('');
            
            domainSelect.innerHTML = '<option value="">-- بدون محول مجال --</option>' + 
                allPlugins.filter(p => p.plugin_type === 'domain').map(p => `<option value="${p.id}">${p.name}</option>`).join('');

            channelSelect.innerHTML = '<option value="">-- بدون محول قناة --</option>' + 
                allPlugins.filter(p => p.plugin_type === 'channel').map(p => `<option value="${p.id}">${p.name}</option>`).join('');
        }

        async function togglePlugin(id, enable) {
            await fetch('/api/plugins/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plugin_id: id, enable: enable })
            });
            loadPlugins();
        }

        async function reloadPlugins() {
            await fetch('/api/plugins/reload', { method: 'POST' });
            loadPlugins();
        }

        async function runPluginTest() {
            const id = document.getElementById('test-plugin-select').value;
            const msg = document.getElementById('test-msg-input').value;
            const out = document.getElementById('plugin-test-out');

            out.innerText = 'جاري التشغيل في بيئة الإضافة...';

            try {
                const res = await fetch('/api/plugins/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plugin_id: id, user_message: msg })
                });
                const data = await res.json();
                out.innerText = JSON.stringify(data, null, 2);
            } catch (err) {
                out.innerText = 'فشل في اختبار الإضافة: ' + err;
            }
        }

        async function loadProfile() {
            const res = await fetch(`/api/profile?mode=${currentMode}`);
            const p = await res.json();
            currentProfile = p;
            document.getElementById('cpu-name').innerText = `${p.cpu_model} (${p.cpu_cores} أنوية)`;
            document.getElementById('ram-info').innerText = `${p.total_ram_gb} GB (المتاح: ${p.free_ram_gb} GB)`;
            document.getElementById('avx-info').innerText = p.has_avx2 ? 'مدعوم ✅' : 'غير متوفر';
            document.getElementById('gpu-info').innerText = p.has_cuda ? `${p.gpu_name}` : 'CPU Mode';
        }

        async function checkServerStatus() {
            try {
                const res = await fetch('/api/llamacpp/status');
                const s = await res.json();

                const pill = document.getElementById('server-status-pill');
                const btnStart = document.getElementById('btn-start');
                const btnStop = document.getElementById('btn-stop');
                const btnInstall = document.getElementById('btn-install');
                const instBox = document.getElementById('install-box');

                if (s.is_running) {
                    pill.innerHTML = `<span class="pulse pulse-green"></span> يعمل بنشاط (PID: ${s.pid}, Port: ${s.port})`;
                    pill.style.color = 'var(--success)';
                    btnStart.disabled = true;
                    btnStop.disabled = false;
                } else {
                    pill.innerHTML = `<span class="pulse pulse-red"></span> متوقف حالياً`;
                    pill.style.color = 'var(--muted)';
                    btnStart.disabled = false;
                    btnStop.disabled = true;
                }

                // Installation Visual State Handler
                if (s.install_state && s.install_state.InProgress) {
                    const step = s.install_state.InProgress.step;
                    const percent = s.install_state.InProgress.percent;

                    instBox.style.display = 'block';
                    document.getElementById('install-step-text').innerText = `⚙️ ${step}`;
                    document.getElementById('install-percent-badge').innerText = `${percent}%`;
                    document.getElementById('progress-bar-fill').style.width = `${percent}%`;
                    
                    btnInstall.disabled = true;
                    btnInstall.innerHTML = `<span>⏳ جاري التثبيت والتجميع (${percent}%)...</span>`;
                    appendInstallLog(step);
                } else if (s.install_state && s.install_state.Completed) {
                    instBox.style.display = 'block';
                    document.getElementById('install-step-text').innerText = '✅ اكتمل التثبيت والتحميل وتجميع llama.cpp بنجاح!';
                    document.getElementById('install-percent-badge').innerText = '100%';
                    document.getElementById('progress-bar-fill').style.width = '100%';
                    
                    btnInstall.disabled = false;
                    btnInstall.innerHTML = '<span>✅ تم التثبيت بنجاح (إعادة التثبيت)</span>';
                    appendInstallLog('اكتمل التثبيت وتجهيز ملف التشغيل llama-server!');
                } else if (s.install_state && s.install_state.Failed) {
                    instBox.style.display = 'block';
                    document.getElementById('install-step-text').innerText = `❌ خطأ في التثبيت: ${s.install_state.Failed.error}`;
                    document.getElementById('install-percent-badge').innerText = 'خطأ';
                    document.getElementById('progress-bar-fill').style.backgroundColor = 'var(--danger)';
                    
                    btnInstall.disabled = false;
                    btnInstall.innerHTML = '<span>⚠️ إعادة محاولة التثبيت</span>';
                    appendInstallLog(`خطأ: ${s.install_state.Failed.error}`);
                }
            } catch (err) {
                console.error(err);
            }
        }

        async function triggerInstall() {
            if (!currentProfile) return;
            const m = currentProfile.recommended_model;
            if (!confirm(`هل تريد تثبيت llama.cpp وتحميل النموذج ${m.name} (${m.file_size}) الآن؟`)) return;

            const instBox = document.getElementById('install-box');
            const btnInstall = document.getElementById('btn-install');

            instBox.style.display = 'block';
            document.getElementById('install-step-text').innerText = `⏳ جاري إطلاق طلب تثبيت ${m.name}...`;
            document.getElementById('install-percent-badge').innerText = '10%';
            document.getElementById('progress-bar-fill').style.width = '10%';
            btnInstall.disabled = true;
            btnInstall.innerHTML = '<span>⏳ جاري إطلاق عملية التثبيت...</span>';

            appendInstallLog(`بدء إطلاق عملية التثبيت للنموذج ${m.name}...`);

            try {
                await fetch('/api/llamacpp/install', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        model_url: m.download_url,
                        model_filename: m.filename,
                        threads: m.recommended_threads
                    })
                });
            } catch (err) {
                alert('فشل في إرسال أمر التثبيت');
            }
        }

        async function startLlamaServer() {
            if (!currentProfile) return;
            const m = currentProfile.recommended_model;
            try {
                const res = await fetch('/api/llamacpp/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        model_filename: m.filename,
                        threads: m.recommended_threads,
                        context_size: m.context_size
                    })
                });
                const data = await res.json();
                if (!data.success) {
                    alert(`تنبيه: ${data.error}`);
                }
                checkServerStatus();
            } catch (err) {
                alert('فشل في إرسال أمر التشغيل');
            }
        }

        async function stopLlamaServer() {
            await fetch('/api/llamacpp/stop', { method: 'POST' });
            checkServerStatus();
        }

        async function sendPipelinePrompt() {
            const msg = document.getElementById('pipeline-prompt').value;
            const domain = document.getElementById('chat-domain-select').value;
            const channel = document.getElementById('chat-channel-select').value;
            const wrap = document.getElementById('pipeline-res-wrapper');
            const respText = document.getElementById('pipe-response-text');
            const debugBox = document.getElementById('pipe-debug-details');

            wrap.style.display = 'block';
            respText.innerText = 'جاري التكفيل والمعالجة عبر محرك M.A.R.K.E.T....';

            const start = Date.now();
            try {
                const res = await fetch('/api/chat/pipeline', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: msg,
                        domain_plugin: domain || null,
                        channel_plugin: channel || null
                    })
                });
                const data = await res.json();
                const latency = Date.now() - start;

                respText.innerText = data.reply;
                document.getElementById('pipe-provider').innerText = `المصدر: ${data.provider}`;
                document.getElementById('pipe-latency').innerText = `زمن الاستجابة: ${latency} ms`;

                if (data.pipeline_details) {
                    debugBox.innerText = `[الإضافات النشطة]: ${data.pipeline_details.active_plugins.join(', ')}\n\n` +
                        `[السياق المحقون للنموذج]:\n${data.pipeline_details.merged_injected_context}\n` +
                        `[تعليمات النظام المحدثة]:\n${data.pipeline_details.enriched_system_instruction}\n\n` +
                        `[Outbound Payload]:\n${JSON.stringify(data.pipeline_details.outbound_payload, null, 2)}`;
                }
            } catch (err) {
                respText.innerText = 'خطأ في الاتصال بالحاسوب المحمل.';
            }
        }

        function applyWebhookPreset() {
            const val = document.getElementById('wh-preset-select').value;
            if (val === 'fashion_ig') {
                document.getElementById('wh-channel-select').value = 'instagram';
                document.getElementById('wh-sender-name').value = 'مريم علي (متابعة إنستجرام)';
                document.getElementById('wh-phone').value = '01122334455';
                document.getElementById('wh-msg-input').value = 'عندكم تيشيرت TS-102 ومقاس L بكام ومعاه خصم؟ ورقمي 01122334455';
            } else if (val === 'estate_tg') {
                document.getElementById('wh-channel-select').value = 'telegram';
                document.getElementById('wh-sender-name').value = 'م. طارق عبد الله';
                document.getElementById('wh-phone').value = '01099887766';
                document.getElementById('wh-msg-input').value = 'احسبلي قسط شقة بـ 2000000 على 10 سنين وتفاصيل التسليم';
            } else if (val === 'qr_tiktok') {
                document.getElementById('wh-channel-select').value = 'tiktok';
                document.getElementById('wh-sender-name').value = 'تيك توك شوب بائع';
                document.getElementById('wh-phone').value = '01200112233';
                document.getElementById('wh-msg-input').value = 'فحص باركود TS-102 وتفاصيل المخزون الحالية';
            }
        }

        async function sendWebhookSim() {
            const ch = document.getElementById('wh-channel-select').value;
            const name = document.getElementById('wh-sender-name').value;
            const phone = document.getElementById('wh-phone').value;
            const msg = document.getElementById('wh-msg-input').value;
            const wrap = document.getElementById('wh-res-wrapper');
            const replyBox = document.getElementById('wh-reply-text');
            const debugBox = document.getElementById('wh-outbound-debug');

            wrap.style.display = 'block';
            replyBox.innerText = '⏳ جاري إرسال إشارة الـ Webhook واستدعاء ممر الـ Pipeline والموديل...';

            try {
                const res = await fetch(`/api/webhooks/${ch}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        sender_id: 'user_' + Math.floor(Math.random() * 1000),
                        sender_name: name,
                        phone: phone || null,
                        message: msg
                    })
                });
                const data = await res.json();
                replyBox.innerText = data.reply;
                document.getElementById('wh-res-status').innerText = `الحالة: تم المعالجة بنجاح (القناة: ${data.webhook_channel})`;
                debugBox.innerText = JSON.stringify(data.outbound_payload, null, 2);
                loadCrmLeads();
            } catch (err) {
                replyBox.innerText = 'خطأ في إرسال الـ Webhook: ' + err;
            }
        }

        async function loadCrmLeads() {
            try {
                const res = await fetch('/api/crm/leads');
                const leads = await res.json();
                const body = document.getElementById('crm-table-body');
                if (!body) return;

                if (leads.length === 0) {
                    body.innerHTML = '<tr><td colspan="5" style="padding: 12px; text-align: center; color: var(--muted);">لا يوجد عملاء مسجلين حالياً. قم بإرسال Webhook تجريبي.</td></tr>';
                    return;
                }

                body.innerHTML = leads.map(l => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 8px;">
                            <strong style="color: var(--accent);">${l.id}</strong><br>
                            <span style="font-size: 9px; color: var(--muted);">${l.timestamp}</span>
                        </td>
                        <td style="padding: 8px;">
                            <strong style="color: #fff;">${l.customer_name}</strong><br>
                            <span class="plugin-badge badge-channel">${l.channel}</span>
                        </td>
                        <td style="padding: 8px;">
                            <span style="color: var(--info);">${l.phone || 'غير محدد'}</span><br>
                            <span style="color: var(--purple); font-weight: bold;">${l.product_code || 'استفسار عام'}</span>
                        </td>
                        <td style="padding: 8px; max-width: 250px;">
                            <div style="font-weight: bold; color: var(--text);">${l.summary}</div>
                            <div style="font-size: 10px; color: var(--muted); line-height: 1.3;">الرد: ${l.reply_sent.substring(0, 90)}...</div>
                        </td>
                        <td style="padding: 8px;">
                            <select style="font-size: 10px; padding: 2px 4px;" onchange="updateLeadStatus('${l.id}', this.value)">
                                <option value="جديد" ${l.status === 'جديد' ? 'selected' : ''}>🟢 جديد</option>
                                <option value="قيد المتابعة" ${l.status === 'قيد المتابعة' ? 'selected' : ''}>🟡 قيد المتابعة</option>
                                <option value="مكتمل" ${l.status === 'مكتمل' ? 'selected' : ''}>✅ مكتمل</option>
                                <option value="ملغى" ${l.status === 'ملغى' ? 'selected' : ''}>🔴 ملغى</option>
                            </select>
                        </td>
                    </tr>
                `).join('');
            } catch (err) {
                console.error(err);
            }
        }

        async function updateLeadStatus(id, status) {
            await fetch('/api/crm/leads/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id, status: status })
            });
            loadCrmLeads();
        }

        function loadAll() {
            loadPlugins();
            loadProfile();
            checkServerStatus();
            loadCrmLeads();
        }

        window.onload = () => {
            loadAll();
            setInterval(checkServerStatus, 1000);
        };
    </script>
</body>
</html>
"#;

pub async fn run_web_server(port: u16) {
    let workspace = LlamaManager::get_workspace_dir();
    let plugins_dir = workspace.join("plugins");

    let engine = PluginEngine::new(&plugins_dir);
    let state = Arc::new(AppState {
        client: reqwest::Client::new(),
        llama: Arc::new(LlamaManager::new()),
        plugins: Arc::new(Mutex::new(engine)),
        crm: Arc::new(Mutex::new(CrmManager::new())),
    });

    let app = Router::new()
        .route("/", get(index_handler))
        .route("/api/profile", get(get_profile))
        .route("/api/llamacpp/status", get(get_llama_status))
        .route("/api/llamacpp/install", post(install_llama))
        .route("/api/llamacpp/start", post(start_llama))
        .route("/api/llamacpp/stop", post(stop_llama))
        .route("/api/plugins", get(list_plugins))
        .route("/api/plugins/toggle", post(toggle_plugin))
        .route("/api/plugins/reload", post(reload_plugins))
        .route("/api/plugins/execute", post(execute_plugin))
        .route("/api/chat/pipeline", post(chat_pipeline))
        .route("/api/webhooks/meta", get(verify_meta_webhook))
        .route("/api/webhooks/:channel", post(handle_incoming_webhook))
        .route("/api/crm/leads", get(get_crm_leads))
        .route("/api/crm/leads/status", post(update_crm_status))
        .route("/api/crm/export", get(export_crm_csv))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = format!("0.0.0.0:{}", port);
    println!("🌐 [M.A.R.K.E.T. Enterprise AI Engine v1.0.0] Active at http://{}", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn index_handler() -> Html<&'static str> {
    Html(DASHBOARD_HTML)
}

async fn get_profile(Query(params): Query<ProfileQuery>) -> Json<SystemProfile> {
    let mode = match params.mode.as_deref() {
        Some("dedicated_server") => WorkloadMode::DedicatedServer,
        _ => WorkloadMode::CasualTrial,
    };
    let profile = SystemProfile::probe_with_mode(mode);
    Json(profile)
}

async fn get_llama_status(State(state): State<Arc<AppState>>) -> Json<LlamaServerStatus> {
    Json(state.llama.status())
}

async fn install_llama(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<InstallRequest>,
) -> Json<serde_json::Value> {
    state
        .llama
        .trigger_install(payload.model_url, payload.model_filename, payload.threads);

    Json(serde_json::json!({
        "success": true,
        "message": "تم بدء تثبيت llama.cpp والنموذج في الخلفية"
    }))
}

async fn start_llama(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<StartRequest>,
) -> Json<serde_json::Value> {
    let filename = payload.model_filename.unwrap_or_else(|| "model.gguf".to_string());
    let threads = payload.threads.unwrap_or(4);
    let ctx = payload.context_size.unwrap_or(4096);

    match state.llama.start(&filename, threads, ctx, 8081) {
        Ok(pid) => Json(serde_json::json!({ "success": true, "pid": pid, "port": 8081 })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn stop_llama(State(state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    let _ = state.llama.stop();
    Json(serde_json::json!({ "success": true }))
}

async fn list_plugins(State(state): State<Arc<AppState>>) -> Json<Vec<PluginManifest>> {
    let engine = state.plugins.lock().unwrap();
    Json(engine.list_plugins())
}

async fn toggle_plugin(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<TogglePluginRequest>,
) -> Json<serde_json::Value> {
    let mut engine = state.plugins.lock().unwrap();
    match engine.toggle_plugin(&payload.plugin_id, payload.enable) {
        Ok(new_state) => Json(serde_json::json!({ "success": true, "enabled": new_state })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn reload_plugins(State(state): State<Arc<AppState>>) -> Json<serde_json::Value> {
    let mut engine = state.plugins.lock().unwrap();
    engine.reload();
    Json(serde_json::json!({ "success": true, "count": engine.list_plugins().len() }))
}

async fn execute_plugin(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<TestPluginRequest>,
) -> Json<serde_json::Value> {
    let engine = state.plugins.lock().unwrap();
    let input = PluginInput {
        user_message: payload.user_message,
        metadata: payload.metadata.unwrap_or(serde_json::json!({})),
        db_context: String::new(),
    };

    match engine.execute_plugin(&payload.plugin_id, &input) {
        Ok(out) => Json(serde_json::to_value(out).unwrap()),
        Err(e) => Json(serde_json::json!({ "status": "error", "error": e })),
    }
}

async fn chat_pipeline(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<ChatRequest>,
) -> Json<ChatResponse> {
    let start = std::time::Instant::now();
    let base_sys = payload
        .system_prompt
        .unwrap_or_else(|| "أنت مساعد ذكاء اصطناعي محترف لمؤسسات الأعمال.".to_string());

    let pipeline_res = {
        let engine = state.plugins.lock().unwrap();
        engine.run_pipeline(
            &payload.message,
            payload.channel_plugin.as_deref(),
            payload.domain_plugin.as_deref(),
            &base_sys,
            payload.metadata.unwrap_or(serde_json::json!({})),
        )
    };

    let mut full_prompt = String::new();
    if !pipeline_res.merged_injected_context.is_empty() {
        full_prompt.push_str(&format!("{}\n\n", pipeline_res.merged_injected_context));
    }
    full_prompt.push_str(&payload.message);

    let body = serde_json::json!({
        "messages": [
            { "role": "system", "content": pipeline_res.enriched_system_instruction },
            { "role": "user", "content": full_prompt }
        ],
        "temperature": 0.7,
        "max_tokens": 512
    });

    match state
        .client
        .post("http://127.0.0.1:8081/v1/chat/completions")
        .json(&body)
        .send()
        .await
    {
        Ok(res) => {
            let latency = start.elapsed().as_millis() as u64;
            let status = res.status();
            if let Ok(json_val) = res.json::<serde_json::Value>().await {
                if status == reqwest::StatusCode::SERVICE_UNAVAILABLE
                    || (json_val["error"].is_object() && json_val["error"]["code"] == 503)
                {
                    return Json(ChatResponse {
                        success: false,
                        reply: "⏳ النموذج قيد التحميل في رامات الجهاز حالياً... يرجى الانتظار بضع ثوانٍ وإعادة المحاولة.".to_string(),
                        provider: "Local M.A.R.K.E.T. llama.cpp".to_string(),
                        latency_ms: latency,
                        pipeline_details: Some(pipeline_res),
                    });
                }
                let content = json_val["choices"][0]["message"]["content"]
                    .as_str()
                    .unwrap_or_else(|| {
                        json_val["error"]["message"]
                            .as_str()
                            .unwrap_or("لا توجد استجابة من الموديل")
                    })
                    .to_string();
                Json(ChatResponse {
                    success: true,
                    reply: content,
                    provider: "Local M.A.R.K.E.T. llama.cpp".to_string(),
                    latency_ms: latency,
                    pipeline_details: Some(pipeline_res),
                })
            } else {
                Json(ChatResponse {
                    success: false,
                    reply: "فشل في فك ترميز استجابة الخادم".to_string(),
                    provider: "Local llama.cpp".to_string(),
                    latency_ms: latency,
                    pipeline_details: Some(pipeline_res),
                })
            }
        }
        Err(_) => Json(ChatResponse {
            success: false,
            reply: format!(
                "تم تجهيز الـ Pipeline بنجاح (الإضافات: {:?})، ولكن خادم llama.cpp المحلي ليس قيد التشغيل حالياً على البورت 8081. يرجى الضغط على زر 'تشغيل الخادم'.",
                pipeline_res.active_plugins
            ),
            provider: "Local M.A.R.K.E.T. Pipeline Host".to_string(),
            latency_ms: start.elapsed().as_millis() as u64,
            pipeline_details: Some(pipeline_res),
        }),
    }
}

async fn verify_meta_webhook(Query(params): Query<MetaVerifyQuery>) -> String {
    params.challenge.unwrap_or_else(|| "No challenge provided".to_string())
}

async fn handle_incoming_webhook(
    State(state): State<Arc<AppState>>,
    Path(channel): Path<String>,
    Json(payload): Json<GenericWebhookPayload>,
) -> Json<serde_json::Value> {
    let msg = payload.message.unwrap_or_else(|| "مرحبا، عندكم عروض جديدة؟".to_string());
    let sender_id = payload.sender_id.unwrap_or_else(|| "guest_101".to_string());
    let sender_name = payload.sender_name.unwrap_or_else(|| "عميل السوشيال ميديا".to_string());
    let phone = payload.phone;

    let channel_plugin = match channel.as_str() {
        "instagram" => "instagram_dm",
        "facebook" => "facebook_messenger",
        "telegram" => "telegram_bot",
        "tiktok" => "tiktok_webhook",
        _ => "instagram_dm",
    };

    let domain_plugin = payload.domain_plugin.or_else(|| {
        if msg.contains("TS-102") || msg.contains("تيشيرت") || msg.contains("خصم") {
            Some("fashion_store".to_string())
        } else if msg.contains("شقة") || msg.contains("تمويل") || msg.contains("قسط") {
            Some("real_estate_calc".to_string())
        } else if msg.contains("QR") || msg.contains("باركود") || msg.contains("جرد") {
            Some("qr_excel_lookup".to_string())
        } else {
            Some("fashion_store".to_string())
        }
    });

    let pipeline_res = {
        let engine = state.plugins.lock().unwrap();
        engine.run_pipeline(
            &msg,
            Some(channel_plugin),
            domain_plugin.as_deref(),
            "أنت ممثل خدمة العملاء الرسمي لمؤسسة الأعمال عبر السوشيال ميديا.",
            serde_json::json!({ "sender_id": sender_id, "sender_name": sender_name }),
        )
    };

    let mut full_prompt = String::new();
    if !pipeline_res.merged_injected_context.is_empty() {
        full_prompt.push_str(&format!("{}\n\n", pipeline_res.merged_injected_context));
    }
    full_prompt.push_str(&msg);

    let body = serde_json::json!({
        "messages": [
            { "role": "system", "content": pipeline_res.enriched_system_instruction },
            { "role": "user", "content": full_prompt }
        ],
        "temperature": 0.7,
        "max_tokens": 512
    });

    let mut reply = String::new();
    if let Ok(res) = state
        .client
        .post("http://127.0.0.1:8081/v1/chat/completions")
        .json(&body)
        .send()
        .await
    {
        if let Ok(json_val) = res.json::<serde_json::Value>().await {
            if let Some(content) = json_val["choices"][0]["message"]["content"].as_str() {
                reply = content.to_string();
            }
        }
    }

    if reply.is_empty() {
        reply = format!(
            "تمت معالجة الطلب عبر محولات النظام [{}]. (ملاحظة: خادم النموذج المحلي غير نشط على 8081 حالياً).",
            channel_plugin
        );
    }

    let product_code = if msg.contains("TS-102") {
        Some("TS-102".to_string())
    } else {
        None
    };

    let duration = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let now_str = format!("TS-{}", duration.as_secs());
    let lead_id = format!("LEAD-{}", duration.as_millis() % 100000);

    let record = LeadRecord {
        id: lead_id.clone(),
        timestamp: now_str,
        channel: channel.clone(),
        customer_id: sender_id.clone(),
        customer_name: sender_name.clone(),
        phone: phone.clone(),
        intent: "استفسار وطلب تلقائي عبر Webhook".to_string(),
        product_code,
        summary: msg.clone(),
        reply_sent: reply.clone(),
        status: "جديد".to_string(),
    };

    {
        let mut crm = state.crm.lock().unwrap();
        let _ = crm.add_lead(record.clone());
    }

    Json(serde_json::json!({
        "success": true,
        "webhook_channel": channel,
        "reply": reply,
        "outbound_payload": pipeline_res.outbound_payload,
        "lead_record": record
    }))
}

async fn get_crm_leads(State(state): State<Arc<AppState>>) -> Json<Vec<LeadRecord>> {
    let crm = state.crm.lock().unwrap();
    Json(crm.list_leads())
}

async fn update_crm_status(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<UpdateLeadStatusRequest>,
) -> Json<serde_json::Value> {
    let mut crm = state.crm.lock().unwrap();
    match crm.update_status(&payload.id, &payload.status) {
        Ok(true) => Json(serde_json::json!({ "success": true })),
        Ok(false) => Json(serde_json::json!({ "success": false, "error": "العميل غير موجود" })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn export_crm_csv(State(state): State<Arc<AppState>>) -> ([(axum::http::HeaderName, &'static str); 2], String) {
    let crm = state.crm.lock().unwrap();
    let csv = crm.export_csv();
    (
        [
            (axum::http::header::CONTENT_TYPE, "text/csv; charset=utf-8"),
            (axum::http::header::CONTENT_DISPOSITION, "attachment; filename=\"leads_export.csv\""),
        ],
        csv,
    )
}
