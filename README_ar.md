<p align="left">
  <a href="./README.md">English</a> | <a href="./README_ar.md">العربية</a>
</p>

# منصة M.A.R.K.E.T

**Modular Automated Response & Knowledge Engine for Trade**  
*(المحرك النمطي المؤتمت للاستجابة والمعرفة في التجارة الإلكترونية)*

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Release](https://img.shields.io/github/v/release/ielfeqi-rgb/M.A.R.K.E.T?style=flat-square&color=orange)](https://github.com/ielfeqi-rgb/M.A.R.K.E.T/releases)
[![License](https://img.shields.io/badge/License-PolyForm%20NonCommercial-green?style=flat-square)](./LICENSE)

خادم أتمتة تجاري ذاتي الاستضافة (Self-Hosted) واستوديو تطوير مرئي لإدارة المحادثات وخدمة العملاء متعددة القنوات (واتساب، فيسبوك ماسنجر، تيك توك) وتدقيق المخزون.

---

## معمارية النظام (Architecture Overview)

تجمع منصة M.A.R.K.E.T بين خادم خلفي غير متزامن فائق السرعة مبني بـ FastAPI ومحرك برمجة مرئي مستوحى من بيئة Scratch 3.0، لتمكين فرق العمل والمتاجر من أتمتة خدمة العملاء واستعلامات المخزون وتوجيه الطلبات بأقل مجهود تشغيلي.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        معمارية نظام M.A.R.K.E.T                        │
├──────────────────────────┬─────────────────────────────────────────────┤
│ استوديو الواجهة الأمامية │ محرر البلوكات المرئي (Scratch Paradigm)     │
│ خادم الباك إند           │ FastAPI (ASGI / Python 3.12+)               │
│ بوابات المراسلة          │ WhatsApp (OpenWA), Meta Messenger, Webhooks │
│ ربط وتدقيق البيانات      │ Excel (openpyxl) و SQLite (market.db)       │
│ طبقة استدلال الذكاء     │ محلي (Llama.cpp / Ollama) + سحابي (APIs)    │
│ بيئات النشر والتشغيل     │ Docker, Docker Compose, Linux Systemd       │
└──────────────────────────┴─────────────────────────────────────────────┘
```

---

## المكونات الأساسية (Core Components)

- **استوديو التدفقات المرئية (Visual Workflow Builder):** بناء شجرات المحادثات ومنطق الردود بالسحب والإفلات للبلوكات التفاعلية، والتي يتم ترجمتها آلياً إلى كود بايثون حقيقي قابل للتنفيذ.
- **محولات القنوات الموحدة (Multi-Channel Adapters):**
  - **واتساب (WhatsApp):** تكامل مباشر مع بوابة OpenWA مع توليد فوري لرمز الاستجابة السريعة (QR Canvas) وتأكيد الطلبات تلقائياً.
  - **فيسبوك وإنستغرام (Meta Messenger):** الاستماع لـ Webhooks للرد التلقائي على التعليقات العامة وتوجيه التفاصيل إلى الرسائل الخاصة (Inbox).
  - **تيك توك والويب هوك (TikTok & Webhooks):** معالجة حمولات الطلبات وإشعارات التجارة الإلكترونية الواردة.
- **محرك تدقيق المخزون ومنع الهلوسة (Grounding Engine):** مطابقة نصوص استفسارات العملاء بالعامية والفصحى مع المنتجات بدقة عبر `products.xlsx` وقواعد بيانات SQLite لمنع اختلاق الأسعار أو التفاصيل.
- **سلسلة التوجيه المرنة للذكاء الاصطناعي (Inference Pipeline):** أولوية للتشغيل المحلي دون إنترنت عبر نماذج (`Qwen 2.5`, `Llama 3.2`)، مع إمكانية التحول التلقائي للسحابة (Google Gemini, Groq, OpenAI).
- **أدوات المراقبة وإدارة العمليات (DevOps & Observability):** قياس مباشر لاستهلاك المعالج والذاكرة والاتصالات النشطة، مع قوالب جاهزة لـ Docker و Systemd و Nginx.

---

## دليل البدء والتشغيل (Getting Started)

### المتطلبات الأساسية

- بايثون 3.10 أو أحدث (يوصى بـ Python 3.12)
- مدير الحزم `pip` وبيئة `venv`
- دوكر و Docker Compose (اختياري، في حال الرغبة بالنشر عبر الحاويات)

### التشغيل المحلي

1. استنساخ المستودع (Clone):
   ```bash
   git clone https://github.com/ielfeqi-rgb/M.A.R.K.E.T.git
   cd M.A.R.K.E.T
   ```

2. إعداد متغيرات البيئة:
   ```bash
   cp .env.example .env
   # قم بتعديل ملف .env لإضافة المفاتيح والإعدادات الخاصة بك
   ```

3. تشغيل سكريبت البدء التلقائي:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

4. فتح لوحة التحكم في المتصفح:
   - **لوحة المراقبة والتحكم:** [http://localhost:8000](http://localhost:8000)
   - **توثيق الـ API التفاعلي (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## النشر في بيئات الإنتاج (Production Deployment)

### الخيار الأول: عبر Docker Compose (الأسهل والأكثر استقراراً)

```bash
cp .env.example .env
docker-compose up -d --build
```

### الخيار الثاني: على خادم لينكس مباشرة (Linux Systemd VPS)

```bash
sudo ./deploy.sh
```

للحصول على تفاصيل شاملة حول ضبط الـ Reverse Proxy عبر Nginx وتفعيل شهادات SSL مجانية (Let's Encrypt)، راجع [`IT_DEPLOYMENT_GUIDE.md`](./IT_DEPLOYMENT_GUIDE.md).

---

## هيكلية المشروع (Project Structure)

```
M.A.R.K.E.T/
├── main.py                 # نقطة الدخول الأساسية لخادم FastAPI والمسارات
├── scratch_engine.py       # محرك ترجمة بلوكات سكراتش إلى كود بايثون
├── bot_logic.py            # منطق إدارة الحوارات وتوجيه المحادثات
├── ai_provider.py          # عميل موحد للربط مع نماذج الذكاء الاصطناعي المحلية والسحابية
├── excel_helper.py         # فهرسة شيت الإكسيل والبحث المطابق في الذاكرة
├── plugin_manager.py       # محمل الإضافات الديناميكي وسجل الإضافات
├── config.json             # ملف الإعدادات المباشرة للنظام
├── products.xlsx           # قاعدة بيانات المنتجات والمخزون
├── plugins/                # ملحقات ومحولات القنوات المعيارية
│   ├── whatsapp_openwa/    # تكامل الواتساب
│   ├── facebook_messenger/ # تكامل ماسنجر فيسبوك
│   ├── tiktok_webhook/     # معالج ويب هوك تيك توك
│   └── qr_excel_lookup/    # فاحص المخزون عبر الباركود و QR
├── Dockerfile              # بناء حاوية الإنتاج
├── docker-compose.yml      # أوركستريشن الخدمات (الخادم الأساسي + بوابة الواتساب)
├── market-ai.service       # وحدة خدمة لينكس (Systemd Unit)
├── nginx.conf.example      # قالب إعداد خادم Nginx العكسي
├── start.sh                # سكريبت التشغيل المحلي
├── deploy.sh               # سكريبت النشر الآلي للإنتاج
└── static/                 # ملفات الواجهة الأمامية ولوحة المراقبة
```

---

## شكر وتقدير للمصادر المفتوحة (Open Source Credits)

يقوم هذا المشروع على جهود مجتمع البرمجيات الحرة ومفتوحة المصدر. نتوجه بالشكر والتقدير للمطورين والمؤسسات التالية:

| المشروع | المطور / المؤسسة | الوصف والدور في النظام |
| :--- | :--- | :--- |
| **[FastAPI](https://fastapi.tiangolo.com/)** | سيباستيان راميريز ([@tiangolo](https://github.com/tiangolo)) | إطار عمل الويب غير المتزامن عالي الأداء |
| **[Uvicorn](https://www.uvicorn.org/)** | فريق Encode OSS | خادم ويب ASGI فائق السرعة |
| **[Scratch](https://scratch.mit.edu/)** | معمل MIT Media Lab | استلهام فلسفة البرمجة المرئية القائمة على البلوكات |
| **[OpenWA / WPPConnect](https://github.com/open-wa/wa-automate-nodejs)** | محمد شاه ومجتمع المطورين | بوابة أتمتة وتشغيل واتساب ويب |
| **[llama.cpp](https://github.com/ggerganov/llama.cpp)** | جورجي غيرغانوف والمساهمون | محرك الاستدلال المحلي عالي الكفاءة بلغة C/C++ |
| **[Qwen Models](https://github.com/QwenLM/Qwen2.5)** | علي بابا كلاود / فريق Qwen | النماذج الأساسية Qwen 2.5 و Qwen 2.5 Coder |
| **[Llama](https://github.com/meta-llama/llama3)** | ميتا للذكاء الاصطناعي (Meta AI) | نماذج لاما 3 مفتوحة المصدر |
| **[openpyxl](https://openpyxl.readthedocs.io/)** | إريك غازوني، تشارلي كلارك | مكتبة التعامل مع ملفات وجداول الإكسيل ببايثون |
| **[Pydantic](https://docs.pydantic.dev/)** | صموئيل كولفين والمساهمون | التحقق من صحة البيانات وإدارة الإعدادات |
| **[Lucide Icons](https://lucide.dev/)** | مشروع Lucide | حزمة الأيقونات الحديثة للواجهة |
| **[Tailwind CSS](https://tailwindcss.com/)** | مختبرات Tailwind Labs | إطار عمل تنسيق وتصميم الواجهات |

---

## الترخيص وشروط الاستخدام (License)

هذا المشروع مرخص بموجب رخصة **PolyForm NonCommercial License 1.0.0 (CC BY-NC-SA 4.0)**.  
الاستخدام مجاني ومتاح للأغراض الشخصية والتعليمية وغير الربحية والمفتوحة المصدر.

للحصول على تراخيص للاستخدام التجاري للشركات، يرجى التواصل مع مالك المشروع.
