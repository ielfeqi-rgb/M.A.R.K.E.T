#  دليل النشر والتشغيل الشامل للإنتاج (IT & DevOps Production Guide)
## M.A.R.K.E.T AI - Enterprise Autonomous Commerce Engine

---

###  نظرة عامة على البنية التحتية
النظام مصمم ليعمل في بيئات الإنتاج المختلفة بسهولة تامة وبأقل استهلاك للموارد:
* **Backend Core**: خادم FastAPI فائق السرعة يعمل على المنفذ `8000`.
* **Frontend Studio**: واجهة Scratch للتحكم المرئي تعمل على المنفذ `3000` (أو مبنية وجاهزة داخل `static/` في الباك إند).
* **WhatsApp Gateway (OpenWA)**: بوابة أتمتة الواتساب تعمل على المنفذ `2785`.

---

##  الخيار الأول: النشر عبر Docker & Docker-Compose (الأسهل والأكثر استقراراً)

### 1. المتطلبات:
* خادم VPS (Ubuntu 22.04 / 24.04 أو Debian أو أي توزيعة Linux).
* تثبيت Docker و Docker-Compose:
```bash
sudo apt update && sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
```

### 2. التشغيل بخطوة واحدة:
قم بالدخول لمجلد المشروع وشغل:
```bash
cp .env.example .env
# عدل المتغيرات والمفاتيح حسب رغبتك
nano .env

# تشغيل الحاويات في الخلفية
docker-compose up -d --build
```

### 3. الأوامر اليومية لإدارة Docker:
* عرض حالة الحاويات: `docker-compose ps`
* عرض سجلات العمليات اللحظية: `docker-compose logs -f market-ai`
* إعادة تشغيل النظام: `docker-compose restart`
* إيقاف الحاويات: `docker-compose down`

---

##  الخيار الثاني: النشر المباشر على خادم Linux عبر Systemd (Native VPS)

### 1. إعداد المسار والبيئة:
```bash
# إنشاء مسار المشروع في السيرفر
sudo mkdir -p /var/www/market-ai
sudo chown -R $USER:$USER /var/www/market-ai

# نسخ الملفات
cp -r ./* /var/www/market-ai/
cd /var/www/market-ai

# إعداد ملف البيئة
cp .env.example .env
nano .env

# تشغيل اسكريبت النشر التلقائي
sudo ./deploy.sh
```

### 2. إدارة خدمة Systemd:
* تشغيل الخدمة: `sudo systemctl start market-ai`
* إيقاف الخدمة: `sudo systemctl stop market-ai`
* إعادة التشغيل: `sudo systemctl restart market-ai`
* متابعة السجلات المباشرة: `sudo journalctl -u market-ai -f`

---

##  الخيار الثالث: إعداد Reverse Proxy عبر Nginx وشهادة SSL (HTTPS)

### 1. تثبيت Nginx و Certbot:
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 2. نسخ إعدادات Nginx:
```bash
sudo cp nginx.conf.example /etc/nginx/sites-available/market-ai.conf
# عدل الدومين الخاص بك
sudo nano /etc/nginx/sites-available/market-ai.conf
sudo ln -s /etc/nginx/sites-available/market-ai.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. استخراج وتفعيل شهادة SSL مجانية (Let's Encrypt):
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

---

##  إعداد متغيرات البيئة الأساسية (`.env`)

| المتغير | القيمة الافتراضية / الوصف |
| :--- | :--- |
| `PORT` | `8000` (منفذ الباك إند) |
| `AI_PROVIDER` | `gemini` / `groq` / `ollama` / `openai` |
| `GEMINI_API_KEY` | مفتاح Google Gemini API |
| `EXCEL_PATH` | `products.xlsx` (قاعدة بيانات المنتجات) |
| `FB_PAGE_TOKEN` | توكن صفحة فيسبوك للردود التلقائية |
| `FB_VERIFY_TOKEN` | كود التحقق من Webhook الفيسبوك |
| `WHATSAPP_ENABLED` | `true` لتفعيل بوابة الواتساب |
| `WHATSAPP_OPENWA_URL` | `http://localhost:2785` |
| `TELEGRAM_BOT_TOKEN` | توكن بوت تيليجرام لتنبيهات الـ IT اللحظية |

---

##  فحص الصحة والسلامة (Healthcheck & Diagnostics)
* فحص سلامة السيرفر: `GET http://localhost:8000/health`
* لوحة المراقبة والتحكم: `http://localhost:8000/`
* توثيق الـ API التفاعلي (Swagger): `http://localhost:8000/docs`
