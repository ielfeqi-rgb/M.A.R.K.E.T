<p align="right">
  <a href="./README_ar.md">العربية</a> | <a href="./README.md">English</a>
</p>

<p align="center">
  <h1 align="center">منظومة M.A.R.K.E.T AI (الإصدار v4.0.0 للمؤسسات)</h1>
  <p align="center">
    <strong>محرك الأتمتة والاستجابة الذكي لخدمة التجارة والمبيعات وإدارة المخازن</strong><br/>
    <em>استوديو الكروت والمسارات المرئية (Visual Cards Studio)، أوركسترا نماذج الذكاء الاصطناعي المحلية، وأتمتة قنوات التجارة في الوقت الفعلي</em>
  </p>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/بايثون-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+"/></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.111%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/></a>
  <a href="https://www.sqlite.org/"><img src="https://img.shields.io/badge/SQLite-WAL%20Engine-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite WAL"/></a>
  <a href="https://github.com/QwenLM/Qwen2.5"><img src="https://img.shields.io/badge/المبرمج%20الذكي-Qwen%202.5%20Coder-6366F1?style=for-the-badge&logo=openai&logoColor=white" alt="Qwen 2.5 Coder"/></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/دوكر-جاهز%20للإنتاج-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/الإصدار-v4.0.0%20Enterprise-10B981?style=for-the-badge" alt="Release v4.0.0"/></a>
</p>

---

## استوديو الكروت والمسارات المرئية (Visual Cards Studio)

<p align="center">
  <img src="./docs/images/visual-node-graph.png" alt="M.A.R.K.E.T v4.0.0 Visual Cards Studio" width="900" style="border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);"/>
</p>

<p align="center">
  <img src="./docs/images/connected-cards-workflow.png" alt="Multi-Card Connected Workflow Pipeline" width="900" style="border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);"/>
</p>

**M.A.R.K.E.T v4.0.0** هي منصة مفتوحة المصدر واستضافة ذاتية (Self-Hosted) عالية الكفاءة للمؤسسات والتجار تجمع بين التنسيق المرئي للكروت وبين التوليد البرمجي المستقل لكود بايثون. تتيح المنظومة بناء وربط ومحاكاة كروت مسارات محادثات العملاء، كروت مطابقة أكواد الخصم، وتأصيل بيانات المخازن وقواعد البيانات عبر لوحة كروت لا نهائية (2D Cards Canvas) تترجم مباشرة إلى كود بايثون سريع وقابل للتنفيذ.

---

## المزايا والقدرات الرئيسية (v4.0.0 Enterprise)

- **لوحة كروت لا نهائية (Infinite 2D Cards Canvas)**: تصميم وربط كروت المسار مع مغناطيسية التوصيل والأسلاك الحسابية المنحنية ومؤشرات التأخير الزمني لكل خطوة.
- **توليد الكروت والكود الذكي (Qwen 2.5 Coder)**: محرك ذكاء مخصص يتلقى متطلبات المستخدم (مثل ربط ملفات إكسيل إضافية، فحص أكواد الخصم، جداول SQL) ويولد كروت تفاعلية جديدة وكود بايثون تنفيذي فوري.
- **أوركسترا تشغيل الموديلات المتزامنة (Dual-Model Concurrency)**: عزل تام بين موديل البرمجة وتوليد الكروت وموديل خدمة العملاء وقنوات التواصل لضمان السرعة الفائقة بدون أي تعارض.
- **قاعدة بيانات SQLite بنمط WAL الصارم**: منع الهلوسة بنسبة 100% عبر الاستعلام اللحظي (أقل من 1ms) والمزامنة المباشرة مع ملف products.xlsx.
- **بوابة قنوات التواصل الشاملة (Omni-Channel Gateways)**: دعم كامل لواتساب عبر OpenWA مع مسح رمز QR مباشرة من الواجهة، وفيسبوك ماسنجر، وتيك توك.
- **منصة فحص ومراقبة متكاملة (DevTools & Live Inspector Suite)**: تتبع تفصيلي لكل خطوة بالمللي ثانية، قياس استهلاك التوكنز والسرعة (Tokens / Sec)، واختبارات ضغط وتزامن الخادم.

---

## التشغيل والبدء السريع

### 1. المتطلبات الأساسية
- Python 3.10+ (يوصى بإصدار 3.12)
- Pip & Venv
- Docker & Docker Compose (اختياري للتشغيل بالحاويات)

### 2. التثبيت والتشغيل

```bash
# استنساخ المستودع
git clone https://github.com/ielfeqi-rgb/M.A.R.K.E.T.git
cd M.A.R.K.E.T

# نسخ ملف الإعدادات
cp .env.example .env

# تشغيل السيرفر الموحد
chmod +x start.sh
./start.sh
```

### 3. الدخول إلى المنصة الموحدة
- الواجهة الموحدة للمنظومة: http://localhost:8000
- توثيق الـ API التفاعلي (Swagger): http://localhost:8000/docs

---

## أقسام المنظومة الموحدة

| القسم | الوصف والوظيفة | الوصول السريع |
| :--- | :--- | :--- |
| **لوحة القيادة والمؤشرات** | عدادات الهاردوير اللحظية، مراقبة الرام والمعالج، وحالة خادم الذكاء المحلي. | القائمة الجانبية -> لوحة القيادة |
| **استوديو الكروت والمسارات** | لوحة ربط الكروت، استوديو Qwen لتوليد الكروت، ومحاكي المحادثة اللحظي. | القائمة الجانبية -> استوديو الكروت |
| **منصة الفحص والتحليل** | تتبع أزمنة المسارات والكروت، محلل التوكنز، كونسول استعلامات SQL، واختبار الضغط. | القائمة الجانبية -> منصة الفحص |
| **المخزن وقاعدة البيانات** | جدول منتجات SQLite WAL، مؤشرات المخزون، والمزامنة مع الإكسيل. | القائمة الجانبية -> المخزن |
| **بوابة واتساب OpenWA** | عرض ومسح رمز الـ QR مباشرة، ومراقبة حالة البوابة واختبار الإرسال. | القائمة الجانبية -> بوابة واتساب |
| **إعدادات النظام والـ AI** | تبديل مزودي الذكاء (Gemini, Groq, Llama, Ollama) وحفظ البرومبت. | القائمة الجانبية -> الإعدادات |

---

## شكر وتقدير للمشاريع مفتوحة المصدر

نبني هذه المنظومة على عمالقة البرمجيات مفتوحة المصدر:

- **FastAPI** -- بواسطة Sebastian Ramirez (@tiangolo).
- **Uvicorn** -- خادم الـ ASGI فائق السرعة.
- **Qwen Models** -- نماذج الذكاء الاصطناعي المتقدمة من Alibaba Cloud.
- **llama.cpp** -- محرك تشغيل نماذج الذكاء محليا بكفاءة C/C++.
- **OpenWA** -- بوابة أتمتة واتساب.
- **SQLite** -- محرك التخزين والبيانات فائق السرعة بنمط WAL.
- **Lucide Icons** -- مكتبة الأيقونات العصرية.
- **Tailwind CSS** -- إطار التنسيق والتصميم المرن.

---

## الترخيص

هذا المشروع مرخص بموجب **PolyForm NonCommercial License 1.0.0 (CC BY-NC-SA 4.0)**.  
متاح مجانا للاستخدام الشخصي والتعليمي وغير التجاري.
