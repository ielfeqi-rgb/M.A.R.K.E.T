/* ==========================================================================
   M.A.R.K.E.T AI 2.0 (OmniContext Engine) - Master JavaScript Application
   ========================================================================== */

// === Toast Notification System ===
function showToast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    toast.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span class="toast-msg">${message}</span>`;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('toast-show'));
    setTimeout(() => {
        toast.classList.remove('toast-show');
        toast.classList.add('toast-hide');
        setTimeout(() => toast.remove(), 400);
    }, duration);
}

// === Button Ripple Effect ===
document.addEventListener('click', function(e) {
    const btn = e.target.closest('.btn');
    if (!btn) return;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
});

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Lucide Icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // --- Theme Switcher (Dark & Light) ---
    initThemeSwitcher();

    // --- Sidebar Navigation & Mobile Menu ---
    const menuItems = document.querySelectorAll(".menu-item");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const activeTabTitle = document.getElementById("activeTabTitle");
    const sidebar = document.getElementById("appSidebar");
    const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
    const mobileCloseBtn = document.getElementById("mobileCloseBtn");

    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener("click", () => sidebar.classList.add("active"));
    }
    if (mobileCloseBtn && sidebar) {
        mobileCloseBtn.addEventListener("click", () => sidebar.classList.remove("active"));
    }

    menuItems.forEach(item => {
        item.addEventListener("click", () => {
            const target = item.getAttribute("data-tab");
            menuItems.forEach(i => i.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            item.classList.add("active");
            const pane = document.getElementById(target);
            if (pane) pane.classList.add("active");

            // Update top bar title
            if (activeTabTitle) {
                const titleText = item.querySelector("span")?.innerText || "";
                activeTabTitle.innerText = titleText;
            }

            // Close mobile sidebar if open
            if (sidebar) sidebar.classList.remove("active");
        });
    });

    // --- Initial Data Load ---
    loadAppStatus();
    loadHardwareAdvisor();
    loadLlamaEngineStatus();
    loadSettings();
    loadOllamaModels();
    loadProducts();
    loadPlugins();
    initLogStream();

    // --- Plugins UI Listeners ---
    const generatePluginBtn = document.getElementById("generatePluginBtn");
    if (generatePluginBtn) {
        generatePluginBtn.addEventListener("click", generateAiPlugin);
    }
    const refreshPluginsBtn = document.getElementById("refreshPluginsBtn");
    if (refreshPluginsBtn) {
        refreshPluginsBtn.addEventListener("click", loadPlugins);
    }

    // --- llama.cpp Engine Actions ---
    const installLlamaBtn = document.getElementById("installLlamaBtn");
    if (installLlamaBtn) {
        installLlamaBtn.addEventListener("click", async () => {
            installLlamaBtn.disabled = true;
            showToast("بدأت عملية استنساخ وبناء llama.cpp في الخلفية...", 'info');
            try {
                const res = await fetch("/api/llamacpp/install", { method: "POST" });
                const result = await res.json();
                if (result.success) {
                    showToast(result.message, 'success');
                    pollLlamaInstallStatus();
                } else {
                    showToast(result.message || "فشل التثبيت", 'error');
                }
            } catch (err) {
                showToast("خطأ في الاتصال: " + err.message, 'error');
            } finally {
                installLlamaBtn.disabled = false;
            }
        });
    }

    const startLlamaBtn = document.getElementById("startLlamaBtn");
    if (startLlamaBtn) {
        startLlamaBtn.addEventListener("click", async () => {
            const ggufSelect = document.getElementById("llamaGgufSelect");
            const modelFile = ggufSelect ? ggufSelect.value : "";
            const threads = document.getElementById("llamaThreads")?.value || 4;
            const context = document.getElementById("llamaContext")?.value || 4096;

            if (!modelFile) {
                showToast("يرجى اختيار ملف الموديل GGUF أولاً أو تنزيله في المجلد ~/omnicontext_ai/models/", 'warning');
                return;
            }

            startLlamaBtn.disabled = true;
            showToast(`جارِ تشغيل محرك llama-server للموديل ${modelFile}...`, 'info');
            try {
                const res = await fetch("/api/llamacpp/start", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        model_filename: modelFile,
                        threads: parseInt(threads),
                        context_size: parseInt(context),
                        port: 8081
                    })
                });
                const result = await res.json();
                if (result.success) {
                    showToast(result.message, 'success', 5000);
                    loadLlamaEngineStatus();
                } else {
                    showToast("❌ " + (result.error || "فشل تشغيل المحرك"), 'error', 6000);
                }
            } catch (err) {
                showToast("خطأ في التشغيل: " + err.message, 'error');
            } finally {
                startLlamaBtn.disabled = false;
            }
        });
    }

    const stopLlamaBtn = document.getElementById("stopLlamaBtn");
    if (stopLlamaBtn) {
        stopLlamaBtn.addEventListener("click", async () => {
            stopLlamaBtn.disabled = true;
            try {
                const res = await fetch("/api/llamacpp/stop", { method: "POST" });
                const result = await res.json();
                if (result.success) {
                    showToast(result.message, 'success');
                    loadLlamaEngineStatus();
                } else {
                    showToast("خطأ: " + result.error, 'error');
                }
            } catch (err) {
                showToast("خطأ: " + err.message, 'error');
            } finally {
                stopLlamaBtn.disabled = false;
            }
        });
    }

    // --- Server Quick Action Buttons ---
    const quickReloadExcelBtn = document.getElementById("quickReloadExcelBtn");
    if (quickReloadExcelBtn) {
        quickReloadExcelBtn.addEventListener("click", async () => {
            quickReloadExcelBtn.disabled = true;
            try {
                const res = await fetch("/api/server/reload_excel", { method: "POST" });
                const result = await res.json();
                if (result.status === "success") {
                    showToast(result.message, 'success');
                    loadProducts();
                    loadAppStatus();
                } else {
                    showToast("خطأ: " + (result.detail || "فشل التحديث"), 'error');
                }
            } catch (err) {
                showToast("خطأ في الاتصال: " + err.message, 'error');
            } finally {
                quickReloadExcelBtn.disabled = false;
            }
        });
    }

    const quickRestartNgrokBtn = document.getElementById("quickRestartNgrokBtn");
    if (quickRestartNgrokBtn) {
        quickRestartNgrokBtn.addEventListener("click", async () => {
            quickRestartNgrokBtn.disabled = true;
            showToast("جارِ الاتصال بـ Ngrok لتفعيل النفق...", 'info');
            try {
                const res = await fetch("/api/server/restart_ngrok", { method: "POST" });
                const result = await res.json();
                if (result.status === "success") {
                    showToast(result.message, 'success');
                    loadAppStatus();
                } else {
                    showToast("خطأ: " + (result.detail || "فشل الاتصال"), 'error');
                }
            } catch (err) {
                showToast("خطأ في الاتصال بـ Ngrok: " + err.message, 'error');
            } finally {
                quickRestartNgrokBtn.disabled = false;
            }
        });
    }

    // --- Server OFF Power Switch Button ---
    const serverOffBtn = document.getElementById("serverOffBtn");
    if (serverOffBtn) {
        serverOffBtn.addEventListener("click", async () => {
            if (!confirm("هل أنت متأكد من إيقاف خادم M.A.R.K.E.T والمحركات بالكامل؟")) return;
            
            showToast("🛑 جارِ إيقاف خادم M.A.R.K.E.T وإغلاق الجلسة...", 'warning', 6000);
            serverOffBtn.disabled = true;

            const statusPill = document.getElementById("statusPill");
            const statusText = document.getElementById("statusText");
            if (statusPill) statusPill.className = "status-pill red";
            if (statusText) statusText.innerText = "الخادم متوقف";

            try {
                await fetch("/api/server/shutdown", { method: "POST" });
            } catch (err) {}
        });
    }

    // --- Webhook Copy ---
    const copyBtn = document.getElementById("copyWebhookBtn");
    const webhookInput = document.getElementById("webhookUrlInput");
    if (copyBtn && webhookInput) {
        copyBtn.addEventListener("click", () => {
            if (webhookInput.value) {
                navigator.clipboard.writeText(webhookInput.value);
                showToast("تم نسخ رابط الـ Webhook بنجاح إلى الحافظة! 🎉", 'success');
            }
        });
    }

    // --- AI Provider Switcher ---
    const aiProviderSelect = document.getElementById("aiProviderSelect");
    const configGroups = {
        gemini: document.getElementById("geminiConfigGroup"),
        groq: document.getElementById("groqConfigGroup"),
        ollama: document.getElementById("ollamaConfigGroup"),
        openai: document.getElementById("openaiConfigGroup"),
        deepseek: document.getElementById("deepseekConfigGroup"),
        custom: document.getElementById("customConfigGroup")
    };

    if (aiProviderSelect) {
        aiProviderSelect.addEventListener("change", (e) => {
            const selected = e.target.value;
            Object.keys(configGroups).forEach(key => {
                if (configGroups[key]) {
                    if (key === selected) {
                        configGroups[key].classList.remove("hidden");
                    } else {
                        configGroups[key].classList.add("hidden");
                    }
                }
            });
        });
    }

    // --- Main Settings Form Submission ---
    const settingsForm = document.getElementById("settingsForm");
    if (settingsForm) {
        settingsForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(settingsForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const res = await fetch("/api/settings", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.status === "success") {
                    showToast("تم حفظ إعدادات الصفحة والرسائل بنجاح! ✨", 'success');
                    loadAppStatus();
                } else {
                    showToast("خطأ: " + (result.detail || "فشل التعديل"), 'error');
                }
            } catch (err) {
                showToast("خطأ في الاتصال بالسيرفر: " + err.message, 'error');
            }
        });
    }

    // --- Comments Settings Form Submission ---
    const commentsForm = document.getElementById("commentsForm");
    if (commentsForm) {
        commentsForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const payload = {
                auto_reply_comments: document.getElementById("autoReplyComments").value === "true",
                comment_reply_mode: document.getElementById("commentReplyMode").value,
                comment_prompt: document.getElementById("commentPrompt").value
            };

            try {
                const res = await fetch("/api/settings", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const result = await res.json();
                if (result.status === "success") {
                    showToast("تم حفظ إعدادات الرد على التعليقات بنجاح! 📩", 'success');
                } else {
                    showToast("خطأ في حفظ إعدادات التعليقات", 'error');
                }
            } catch (err) {
                showToast("خطأ في الاتصال: " + err.message, 'error');
            }
        });
    }

    // --- AI Provider Settings Save & Test ---
    const saveAiBtn = document.getElementById("saveAiBtn");
    const testAiBtn = document.getElementById("testAiBtn");

    if (saveAiBtn) {
        saveAiBtn.addEventListener("click", async () => {
            const provider = aiProviderSelect.value;
            const payload = {
                ai_provider: provider,
                ollama_url: document.getElementById("ollamaUrl")?.value || "http://localhost:11434",
                ollama_model: document.getElementById("ollamaModel")?.value || "llama3.2:3b",
                gemini_api_key: document.getElementById("geminiApiKey")?.value || "",
                gemini_model: document.getElementById("geminiModel")?.value || "gemini-2.5-flash",
                openai_api_key: document.getElementById("openaiApiKey")?.value || "",
                openai_model: document.getElementById("openaiModel")?.value || "gpt-4o-mini",
                groq_api_key: document.getElementById("groqApiKey")?.value || "",
                groq_model: document.getElementById("groqModel")?.value || "llama-3.3-70b-versatile",
                deepseek_api_key: document.getElementById("deepseekApiKey")?.value || "",
                deepseek_model: document.getElementById("deepseekModel")?.value || "deepseek-chat",
                custom_ai_url: document.getElementById("customAiUrl")?.value || "",
                custom_ai_key: document.getElementById("customAiKey")?.value || "",
                custom_ai_model: document.getElementById("customAiModel")?.value || ""
            };

            try {
                const res = await fetch("/api/settings", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const result = await res.json();
                if (result.status === "success") {
                    showToast("تم حفظ إعدادات الذكاء الاصطناعي بنجاح!", 'success');
                    loadAppStatus();
                }
            } catch (err) {
                showToast("فشل الحفظ: " + err.message, 'error');
            }
        });
    }

    if (testAiBtn) {
        testAiBtn.addEventListener("click", async () => {
            testAiBtn.innerText = "جارِ الاختبار...";
            testAiBtn.disabled = true;

            const provider = aiProviderSelect ? aiProviderSelect.value : "gemini";
            const payload = {
                ai_provider: provider,
                ollama_url: document.getElementById("ollamaUrl")?.value || "http://localhost:11434",
                ollama_model: document.getElementById("ollamaModel")?.value || "llama3.2:3b",
                gemini_api_key: document.getElementById("geminiApiKey")?.value || "",
                gemini_model: document.getElementById("geminiModel")?.value || "gemini-2.5-flash",
                openai_api_key: document.getElementById("openaiApiKey")?.value || "",
                openai_model: document.getElementById("openaiModel")?.value || "gpt-4o-mini",
                groq_api_key: document.getElementById("groqApiKey")?.value || "",
                groq_model: document.getElementById("groqModel")?.value || "llama-3.3-70b-versatile",
                deepseek_api_key: document.getElementById("deepseekApiKey")?.value || "",
                deepseek_model: document.getElementById("deepseekModel")?.value || "deepseek-chat",
                custom_ai_url: document.getElementById("customAiUrl")?.value || "",
                custom_ai_key: document.getElementById("customAiKey")?.value || "",
                custom_ai_model: document.getElementById("customAiModel")?.value || ""
            };

            try {
                const res = await fetch("/api/models/test", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const result = await res.json();
                if (result.status === "success") {
                    showToast("✅ الاتصال ناجح ومستعد! المزود: " + (result.provider_label || result.provider || provider), 'success', 5000);
                } else {
                    showToast("❌ فشل الاتصال بالموديل: " + (result.error || "خطأ غير معروف"), 'error', 5000);
                }
            } catch (err) {
                showToast("خطأ في الاتصال: " + err.message, 'error');
            } finally {
                testAiBtn.innerText = "اختبار الاتصال بالتسلسل التلقائي";
                testAiBtn.disabled = false;
            }
        });
    }

    // --- Pull Ollama Model ---
    const startPullBtn = document.getElementById("startPullBtn");
    const pullModelName = document.getElementById("pullModelName");

    if (startPullBtn && pullModelName) {
        startPullBtn.addEventListener("click", () => {
            const modelName = pullModelName.value.trim();
            if (!modelName) {
                showToast("يرجى كتابة اسم الموديل أولاً (مثل llama3.2:1b)", 'warning');
                return;
            }
            triggerPullModel(modelName);
        });
    }

    // --- Excel Upload ---
    const excelFileInput = document.getElementById("excelFileInput");
    if (excelFileInput) {
        excelFileInput.addEventListener("change", async (e) => {
            if (e.target.files.length === 0) return;
            const file = e.target.files[0];
            const formData = new FormData();
            formData.append("file", file);

            showToast("جارِ رفع شيت المنتجات وتحديث قاعدة البيانات...", 'info');
            try {
                const res = await fetch("/api/excel/upload", {
                    method: "POST",
                    body: formData
                });
                const result = await res.json();
                if (result.status === "success") {
                    showToast("تم رفع الشيت وتحديث المنتجات بنجاح! 📊", 'success');
                    loadProducts();
                    loadAppStatus();
                } else {
                    showToast("خطأ: " + result.detail, 'error');
                }
            } catch (err) {
                showToast("فشل رفع الملف: " + err.message, 'error');
            }
        });
    }

    // --- Products CRUD Modal ---
    const productModal = document.getElementById("productModal");
    const openAddBtn = document.getElementById("openAddProductModalBtn");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const productForm = document.getElementById("productForm");

    if (openAddBtn && productModal) {
        openAddBtn.addEventListener("click", () => {
            document.getElementById("modalTitle").innerText = "إضافة منتج جديد";
            productForm.reset();
            productModal.classList.remove("hidden");
        });
    }
    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => productModal.classList.add("hidden"));
    }

    if (productForm) {
        productForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const productData = {
                "كود المنتج": document.getElementById("prodCode").value,
                "اسم المنتج": document.getElementById("prodName").value,
                "السعر": parseFloat(document.getElementById("prodPrice").value) || 0,
                "المقاس": document.getElementById("prodSize").value,
                "اللون": document.getElementById("prodColor").value,
                "الكمية المتاحة": parseInt(document.getElementById("prodQty").value) || 0,
                "الوصف": document.getElementById("prodDesc").value
            };

            try {
                const res = await fetch("/api/products", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(productData)
                });
                const result = await res.json();
                if (result.status === "success") {
                    showToast("تم حفظ المنتج بنجاح!", 'success');
                    productModal.classList.add("hidden");
                    loadProducts();
                    loadAppStatus();
                } else {
                    showToast("خطأ: " + result.detail, 'error');
                }
            } catch (err) {
                showToast("فشل الحفظ: " + err.message, 'error');
            }
        });
    }

    // Search filter for products table
    const searchInput = document.getElementById("searchProductInput");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase();
            const rows = document.querySelectorAll("#productsTableBody tr");
            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(query) ? "" : "none";
            });
        });
    }

    // --- Interactive Chat Tester ---
    const sendTestMsgBtn = document.getElementById("sendTestMsgBtn");
    const testMessageInput = document.getElementById("testMessageInput");
    const testProductCodeInput = document.getElementById("testProductCodeInput");
    const chatBox = document.getElementById("chatBox");

    if (sendTestMsgBtn) {
        sendTestMsgBtn.addEventListener("click", async () => {
            const message = testMessageInput.value.trim();
            const code = testProductCodeInput.value.trim();
            if (!message && !code) return;

            appendChatBubble(message || `[فحص الكود: ${code}]`, "user");
            testMessageInput.value = "";

            try {
                const res = await fetch("/api/test/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: message, product_code: code })
                });
                const data = await res.json();
                if (data.status === "success") {
                    appendChatBubble(data.reply, "bot");
                } else {
                    appendChatBubble("⚠️ تعذر الحصول على رد من السيرفر", "bot");
                }
            } catch (err) {
                appendChatBubble("خطأ في الاتصال: " + err.message, "bot");
            }
        });
    }

    function appendChatBubble(text, sender) {
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${sender}-bubble`;
        bubble.innerText = text;
        chatBox.appendChild(bubble);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // --- Clear Logs ---
    const clearLogsBtn = document.getElementById("clearLogsBtn");
    const terminalWindow = document.getElementById("terminalWindow");
    if (clearLogsBtn && terminalWindow) {
        clearLogsBtn.addEventListener("click", () => {
            terminalWindow.innerHTML = '<div class="log-entry system">[System] تم مسح السجلات...</div>';
            showToast("تم تفريغ شاشة السجلات", 'info');
        });
    }
});

// --- Theme Switcher Logic ---
function initThemeSwitcher() {
    const themeBtn = document.getElementById("themeToggleBtn");
    const themeText = document.getElementById("themeToggleText");
    const htmlElem = document.documentElement;

    // Load saved theme or default to dark
    const savedTheme = localStorage.getItem("omnicontext_theme") || "dark";
    htmlElem.setAttribute("data-theme", savedTheme);
    updateThemeUI(savedTheme);

    if (themeBtn) {
        themeBtn.addEventListener("click", () => {
            const currentTheme = htmlElem.getAttribute("data-theme") || "dark";
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            
            htmlElem.setAttribute("data-theme", newTheme);
            localStorage.setItem("omnicontext_theme", newTheme);
            updateThemeUI(newTheme);
            showToast(newTheme === "light" ? "تم تفعيل الوضع النهاري ☀️" : "تم تفعيل الوضع الليلي 🌙", 'info');
        });
    }

    function updateThemeUI(theme) {
        if (themeText) {
            themeText.innerText = theme === "dark" ? "الوضع النهاري" : "الوضع الليلي";
        }
    }
}

// --- llama.cpp Local Process Control Loader ---
async function loadLlamaEngineStatus() {
    try {
        const res = await fetch("/api/llamacpp/status");
        const status = await res.json();

        const pill = document.getElementById("llamaEngineStatusPill");
        const statusText = document.getElementById("llamaEngineStatusText");
        const infoText = document.getElementById("llamaEngineInfoText");
        const startBtn = document.getElementById("startLlamaBtn");
        const stopBtn = document.getElementById("stopLlamaBtn");
        const ggufSelect = document.getElementById("llamaGgufSelect");

        if (status.running) {
            if (pill) pill.className = "status-pill green";
            if (statusText) statusText.innerText = `يعمل بنشاط (Port: ${status.port}, PID: ${status.pid})`;
            if (infoText) infoText.innerHTML = `🟢 المحرك يعمل حالياً بملف <strong>${status.running_model}</strong> على المنفذ ${status.port}.`;
            if (startBtn) startBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
        } else {
            if (pill) pill.className = "status-pill red";
            if (statusText) statusText.innerText = "المحرك متوقف حالياً";
            if (startBtn) startBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;

            if (status.installed) {
                if (infoText) infoText.innerHTML = `✅ ثنائي llama-server مثبت ومستعد على المسار: <code>${status.binary_path}</code>`;
            } else {
                if (infoText) infoText.innerHTML = `⚠️ ثنائي llama-server غير متاح حالياً. اضغط 'تثبيت/بناء محرك llama.cpp' ليتم بناءه تلقائياً.`;
            }
        }

        // Render available GGUF models in select dropdown
        if (ggufSelect && status.available_gguf_models) {
            ggufSelect.innerHTML = "";
            if (status.available_gguf_models.length > 0) {
                status.available_gguf_models.forEach(m => {
                    const opt = document.createElement("option");
                    opt.value = m.filename;
                    opt.innerText = `${m.filename} (${m.size_mb} MB)`;
                    if (status.running_model === m.filename) opt.selected = true;
                    ggufSelect.appendChild(opt);
                });
            } else {
                ggufSelect.innerHTML = '<option value="">لا توجد ملفات .gguf في مجلد ~/omnicontext_ai/models/</option>';
            }
        }
    } catch (e) {
        console.error("Llama status error:", e);
    }
}

function pollLlamaInstallStatus() {
    const infoText = document.getElementById("llamaEngineInfoText");
    const interval = setInterval(async () => {
        try {
            const res = await fetch("/api/llamacpp/status");
            const status = await res.json();
            const state = status.install_state;
            if (state) {
                if (infoText) infoText.innerText = `⚙️ [${state.percent}%] ${state.step}`;
                if (state.status === "completed") {
                    clearInterval(interval);
                    showToast("اكتمل تثبيت محرك llama.cpp بنجاح! 🎉", 'success', 5000);
                    loadLlamaEngineStatus();
                } else if (state.status === "failed") {
                    clearInterval(interval);
                    showToast("فشل تثبيت llama.cpp: " + state.error, 'error', 6000);
                    loadLlamaEngineStatus();
                }
            }
        } catch (e) {
            clearInterval(interval);
        }
    }, 2500);
}

// --- Helper Data Loading Functions ---

async function loadAppStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        
        if (data.running) {
            document.getElementById("serverIp").innerText = `http://${data.local_ip}:8000`;
            document.getElementById("statProductsCount").innerText = data.excel_products || 0;
            document.getElementById("statAiProvider").innerText = (data.config.ai_provider || "Ollama").toUpperCase();
            
            const webhookInput = document.getElementById("webhookUrlInput");
            if (webhookInput) {
                webhookInput.value = data.webhook_url || "جارِ إعداد الـ Webhook (أو قيد التشغيل المحلي)...";
            }
        }
    } catch (err) {
        console.error("Status load error:", err);
    }
}

async function loadHardwareAdvisor() {
    try {
        const res = await fetch("/api/hardware");
        const hw = await res.json();

        // 1. Update Sidebar & Main Hardware stats
        const sidebarRamText = document.getElementById("sidebarRamText");
        if (sidebarRamText) sidebarRamText.innerText = `RAM: ${hw.ram_total_gb} GB`;

        const sidebarCoresText = document.getElementById("sidebarCoresText");
        if (sidebarCoresText) sidebarCoresText.innerText = `CPU: ${hw.cpu_cores} Cores`;

        const bannerText = document.getElementById("hardwareBannerText");
        if (bannerText) {
            bannerText.innerText = `عتاد السيرفر: ${hw.ram_total_gb} GB RAM (${hw.cpu_cores} Cores) - ${hw.tier_label}`;
        }

        const hwRamText = document.getElementById("hwRamText");
        if (hwRamText) hwRamText.innerText = `${hw.ram_total_gb} GB (المتاح: ${hw.ram_available_gb} GB)`;

        const hwCoresText = document.getElementById("hwCoresText");
        if (hwCoresText) hwCoresText.innerText = `${hw.cpu_cores} أنوية معالجة`;

        const hwArchText = document.getElementById("hwArchText");
        if (hwArchText) hwArchText.innerText = `${hw.os} (${hw.arch})`;

        const hwTierBadge = document.getElementById("hwTierBadge");
        if (hwTierBadge) {
            hwTierBadge.innerText = hw.tier.toUpperCase();
            hwTierBadge.className = `badge-pill ${hw.tier_color}`;
        }

        const hwAdviceText = document.getElementById("hwAdviceText");
        if (hwAdviceText) {
            if (hw.recommended_cloud) {
                hwAdviceText.innerHTML = `💡 <strong>توصية:</strong> رامات جهازك (${hw.ram_total_gb}GB) محدودة، لذا يفضل استخدام مزود سحابي مجاني مثل <strong>Google Gemini API</strong> أو <strong>Groq API</strong> لسرعة فائقة.`;
            } else {
                hwAdviceText.innerHTML = `✅ <strong>ممتاز:</strong> رامات جهازك (${hw.ram_total_gb}GB) كافية لتشغيل الموديلات المحلية الموضحة أدناه بسلاسة وبدون إنترنت.`;
            }
        }

        // 2. Render Compatible Recommended Local Models
        const recList = document.getElementById("recommendedModelsList");
        if (recList && hw.compatible_models) {
            recList.innerHTML = "";
            hw.compatible_models.forEach(m => {
                const card = document.createElement("div");
                card.className = "rec-model-card";
                card.innerHTML = `
                    <div class="rec-model-info">
                        <span class="rec-model-title">${m.displayName}</span>
                        <span class="rec-model-desc">${m.description} (${m.size_gb} GB)</span>
                    </div>
                    <div class="rec-model-actions">
                        <button class="btn btn-sm btn-outline" onclick="selectModelForOllama('${m.name}')">اختيار</button>
                        <button class="btn btn-sm btn-accent" onclick="triggerPullModel('${m.name}')">تنزيل</button>
                    </div>
                `;
                recList.appendChild(card);
            });
        }
    } catch (e) {
        console.error("Hardware advisor error:", e);
    }
}

function selectModelForOllama(modelName) {
    const input = document.getElementById("ollamaModel");
    if (input) {
        input.value = modelName;
        showToast(`تم تحديد الموديل '${modelName}'. اضغط 'حفظ إعدادات الـ AI' لتثبيته.`, 'info');
    }
}

function triggerPullModel(modelName) {
    const progressContainer = document.getElementById("pullProgressContainer");
    const progressBar = document.getElementById("pullProgressBar");
    const progressText = document.getElementById("pullStatusText");

    progressContainer.classList.remove("hidden");
    progressBar.style.width = "5%";
    progressText.innerText = `جارِ الاتصال بـ Ollama لتنزيل ${modelName}...`;

    fetch("/api/models/pull", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_name: modelName })
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        function read() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    progressText.innerText = `اكتمل تنزيل الموديل (${modelName}) بنجاح! 🎉`;
                    progressBar.style.width = "100%";
                    showToast(`اكتمل تنزيل الموديل ${modelName} بنجاح!`, 'success');
                    loadOllamaModels();
                    selectModelForOllama(modelName);
                    return;
                }
                const chunk = decoder.decode(value);
                const lines = chunk.split("\n\n");
                lines.forEach(line => {
                    if (line.startsWith("data: ")) {
                        try {
                            const json = JSON.parse(line.replace("data: ", ""));
                            if (json.error) {
                                progressText.innerText = "❌ تعذر الاتصال بـ Ollama. تأكد من تشغيله (ollama serve).";
                                progressBar.style.width = "0%";
                                showToast("تعذر الاتصال بـ Ollama", 'error');
                                return;
                            }
                            if (json.status) progressText.innerText = json.status;
                            if (json.completed && json.total) {
                                const pct = Math.round((json.completed / json.total) * 100);
                                progressBar.style.width = pct + "%";
                                progressText.innerText = `تنزيل: ${pct}% (${(json.completed/1048576).toFixed(1)}MB / ${(json.total/1048576).toFixed(1)}MB)`;
                            }
                        } catch (e) {}
                    }
                });
                read();
            });
        }
        read();
    }).catch(err => {
        progressText.innerText = "خطأ في التحميل: " + err.message;
        showToast("خطأ في تنزيل الموديل: " + err.message, 'error');
    });
}

async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        const config = await res.json();

        if (document.getElementById("fbPageToken")) document.getElementById("fbPageToken").value = config.fb_page_token || "";
        if (document.getElementById("fbVerifyToken")) document.getElementById("fbVerifyToken").value = config.fb_verify_token || "";
        if (document.getElementById("fbAppSecret")) document.getElementById("fbAppSecret").value = config.fb_app_secret || "";
        if (document.getElementById("ngrokToken")) document.getElementById("ngrokToken").value = config.ngrok_authtoken || "";
        if (document.getElementById("systemPrompt")) document.getElementById("systemPrompt").value = config.system_prompt || "";

        // Comments Form
        if (document.getElementById("autoReplyComments")) document.getElementById("autoReplyComments").value = String(config.auto_reply_comments !== false);
        if (document.getElementById("commentReplyMode")) document.getElementById("commentReplyMode").value = config.comment_reply_mode || "both";
        if (document.getElementById("commentPrompt")) document.getElementById("commentPrompt").value = config.comment_prompt || "";

        // AI Provider Form
        const providerSelect = document.getElementById("aiProviderSelect");
        if (providerSelect) {
            providerSelect.value = config.ai_provider || "gemini";
            providerSelect.dispatchEvent(new Event("change"));
        }

        if (document.getElementById("ollamaUrl")) document.getElementById("ollamaUrl").value = config.ollama_url || "http://localhost:11434";
        if (document.getElementById("ollamaModel")) document.getElementById("ollamaModel").value = config.ollama_model || "llama3.2:3b";
        if (document.getElementById("geminiApiKey")) document.getElementById("geminiApiKey").value = config.gemini_api_key || "";
        if (document.getElementById("geminiModel")) document.getElementById("geminiModel").value = config.gemini_model || "gemini-2.5-flash";
        if (document.getElementById("openaiApiKey")) document.getElementById("openaiApiKey").value = config.openai_api_key || "";
        if (document.getElementById("openaiModel")) document.getElementById("openaiModel").value = config.openai_model || "gpt-4o-mini";
        if (document.getElementById("groqApiKey")) document.getElementById("groqApiKey").value = config.groq_api_key || "";
        if (document.getElementById("groqModel")) document.getElementById("groqModel").value = config.groq_model || "llama-3.3-70b-versatile";
        if (document.getElementById("deepseekApiKey")) document.getElementById("deepseekApiKey").value = config.deepseek_api_key || "";
        if (document.getElementById("deepseekModel")) document.getElementById("deepseekModel").value = config.deepseek_model || "deepseek-chat";
        if (document.getElementById("customAiUrl")) document.getElementById("customAiUrl").value = config.custom_ai_url || "http://localhost:1234/v1";
        if (document.getElementById("customAiKey")) document.getElementById("customAiKey").value = config.custom_ai_key || "";
        if (document.getElementById("customAiModel")) document.getElementById("customAiModel").value = config.custom_ai_model || "local-model";

    } catch (err) {
        console.error("Settings load error:", err);
    }
}

async function loadOllamaModels() {
    const list = document.getElementById("installedModelsList");
    if (!list) return;

    try {
        const res = await fetch("/api/models/local");
        const data = await res.json();
        list.innerHTML = "";

        if (data.models && data.models.length > 0) {
            data.models.forEach(m => {
                const li = document.createElement("li");
                li.className = "model-item";
                const sizeMb = (m.size / (1024 * 1024 * 1024)).toFixed(2);
                li.innerHTML = `<span><strong>${m.name}</strong> (${sizeMb} GB)</span> <span class="code-badge">${m.digest}</span>`;
                list.appendChild(li);
            });
        } else {
            list.innerHTML = '<li class="empty-list">لا توجد موديلات محملة محلياً أو خادم Ollama غير مشغل. (يمكن استخدام Gemini / Groq مباشرة).</li>';
        }
    } catch (err) {
        list.innerHTML = '<li class="empty-list">تعذر الاتصال بـ Ollama.</li>';
    }
}

async function loadProducts() {
    const tbody = document.getElementById("productsTableBody");
    if (!tbody) return;

    try {
        const res = await fetch("/api/products");
        const data = await res.json();
        tbody.innerHTML = "";

        if (data.products && data.products.length > 0) {
            data.products.forEach(p => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><span class="code-badge">${p['كود المنتج'] || ''}</span></td>
                    <td>${p['اسم المنتج'] || ''}</td>
                    <td>${p['السعر'] || 0} ج.م</td>
                    <td>${p['المقاس'] || ''}</td>
                    <td>${p['اللون'] || ''}</td>
                    <td>${p['الكمية المتاحة'] || 0}</td>
                    <td>${p['الوصف'] || ''}</td>
                    <td>
                        <div class="action-btns">
                            <button class="btn btn-sm btn-outline" onclick="deleteProduct('${p['كود المنتج']}')">حذف</button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center">لا توجد منتجات في الشيت حالياً.</td></tr>';
        }
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">خطأ في تحميل المنتجات.</td></tr>';
    }
}

async function deleteProduct(code) {
    if (!confirm(`هل أنت متأكد من حذف المنتج (${code}) من الشيت؟`)) return;
    try {
        const res = await fetch(`/api/products/${code}`, { method: "DELETE" });
        const data = await res.json();
        if (data.status === "success") {
            showToast(`تم حذف المنتج ${code} بنجاح!`, 'success');
            loadProducts();
            loadAppStatus();
        } else {
            showToast(data.detail || "فشل الحذف", 'error');
        }
    } catch (err) {
        showToast("خطأ: " + err.message, 'error');
    }
}

function initLogStream() {
    const terminal = document.getElementById("terminalWindow");
    if (!terminal) return;

    const eventSource = new EventSource("/api/logs/stream");
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            const entry = document.createElement("div");
            const senderClass = (data.sender || "system").toLowerCase();
            entry.className = `log-entry ${senderClass}`;
            entry.innerText = `[${data.sender}] ${data.message}`;
            terminal.appendChild(entry);
            terminal.scrollTop = terminal.scrollHeight;
        } catch (e) {}
    };
}

// --- Plugins & AI Plugin Generator ---
async function loadPlugins() {
    const list = document.getElementById("pluginsList");
    if (!list) return;

    try {
        const res = await fetch("/api/plugins");
        const data = await res.json();
        list.innerHTML = "";

        if (data.plugins && data.plugins.length > 0) {
            data.plugins.forEach(p => {
                const item = document.createElement("div");
                item.className = "plugin-card-item card glass-card mb-3 p-3";
                const hooksList = (p.hooks || []).map(h => `<span class="code-badge">${h}</span>`).join(" ");
                const statusBadge = p.enabled ? '<span class="badge badge-success">مفعل</span>' : '<span class="badge badge-secondary">معطل</span>';
                
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            <h4 class="m-0">${p.name || p.id} ${statusBadge}</h4>
                            <small class="text-muted">المؤلف: ${p.author || 'غير معروف'} | الإصدار: ${p.version || '1.0'}</small>
                        </div>
                        <div>
                            <button class="btn btn-sm ${p.enabled ? 'btn-danger' : 'btn-success'}" onclick="togglePluginState('${p.id}', ${!p.enabled})">
                                ${p.enabled ? 'إيقاف' : 'تفعيل'}
                            </button>
                        </div>
                    </div>
                    <p class="text-muted small mb-2">${p.description || 'لا يوجد وصف متاح.'}</p>
                    <div class="plugin-hooks small">
                        <strong>Hook Trigger:</strong> ${hooksList || 'لا يوجد'}
                    </div>
                `;
                list.appendChild(item);
            });
            if (window.lucide) lucide.createIcons();
        } else {
            list.innerHTML = '<div class="text-center py-4 text-muted">لا توجد إضافات مثبتة حالياً في مجلد plugins/</div>';
        }
    } catch (err) {
        list.innerHTML = `<div class="text-center py-4 text-danger">خطأ في تحميل الإضافات: ${err.message}</div>`;
    }
}

async function togglePluginState(pluginId, enable) {
    try {
        const res = await fetch("/api/plugins/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ plugin_id: pluginId, enabled: enable })
        });
        const data = await res.json();
        if (data.status === "success") {
            showToast(`تم ${enable ? 'تفعيل' : 'إيقاف'} الإضافة بنجاح!`, 'success');
            loadPlugins();
        } else {
            showToast(data.detail || "فشل تغيير حالة الإضافة", 'error');
        }
    } catch (err) {
        showToast("خطأ: " + err.message, 'error');
    }
}

async function generateAiPlugin() {
    const promptInput = document.getElementById("aiPluginPrompt");
    const statusDiv = document.getElementById("aiPluginStatus");
    const generateBtn = document.getElementById("generatePluginBtn");

    if (!promptInput || !promptInput.value.trim()) {
        showToast("يرجى كتابة وصف للإضافة المطلوبة أولاً", 'warning');
        return;
    }

    const userPrompt = promptInput.value.trim();
    if (generateBtn) generateBtn.disabled = true;
    if (statusDiv) statusDiv.innerHTML = '<div class="alert alert-info"><i data-lucide="loader" class="spin"></i> جارِ توليد كود الإضافة باستخدام نموذج الذكاء الاصطناعي... قد يستغرق ذلك ثوانٍ.</div>';
    if (window.lucide) lucide.createIcons();

    try {
        const res = await fetch("/api/plugins/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: userPrompt })
        });
        const data = await res.json();

        if (res.ok && data.status === "success") {
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="alert alert-success">
                        <strong>🎉 ${data.message}</strong><br>
                        <small>تم حفظ الملف: <code>plugins/${data.filename}</code></small>
                    </div>
                `;
            }
            showToast(data.message, 'success', 5000);
            promptInput.value = "";
            loadPlugins();
        } else {
            const errorMsg = data.detail || data.error || "فشل توليد الإضافة";
            if (statusDiv) {
                statusDiv.innerHTML = `<div class="alert alert-danger">❌ ${errorMsg}</div>`;
            }
            showToast("فشل توليد الإضافة: " + errorMsg, 'error');
        }
    } catch (err) {
        if (statusDiv) {
            statusDiv.innerHTML = `<div class="alert alert-danger">❌ خطأ في الاتصال: ${err.message}</div>`;
        }
        showToast("خطأ في الاتصال: " + err.message, 'error');
    } finally {
        if (generateBtn) generateBtn.disabled = false;
        if (window.lucide) lucide.createIcons();
    }
}

