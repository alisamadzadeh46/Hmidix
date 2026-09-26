# فروشگاه Hamidix — بک‌اند جنگو

فروشگاه دوربین مداربسته و لوازم جانبی، ساخته‌شده با **Django 5.2** و معماری
**Class-Based View** و تمپلیت‌های جنگو. دیتابیس روی **MySQL/MariaDB** (قابل مدیریت
با phpMyAdmin) اجرا می‌شود و در حالت توسعه به‌صورت پیش‌فرض از SQLite استفاده می‌کند.

## ساختار پروژه

```
hamidix/
├── config/            تنظیمات پروژه (settings, urls, wsgi, middleware)
├── core/              ابزارهای مشترک بین اپ‌ها (ریدایرکت امن و ...)
├── shop/              محصولات و دسته‌بندی‌ها (مدل، ویو، ادمین)
│   └── management/commands/seed_products.py   انتقال محصولات قدیمی به DB
├── accounts/          کاربر سفارشی با ورود بر اساس شماره تلفن
├── orders/            سبد خرید (session)، سفارش‌ها و اتصال به درگاه پرداخت
├── templates/         تمپلیت‌های HTML (base + صفحات)
├── static/            css / js / images / fonts
├── media/             تصاویر آپلودی محصولات
├── _legacy/           صفحات HTML قدیمی که seed_products محصولات را از آن‌ها می‌خواند
├── deploy.py          اسکریپت استقرار افزایشی (تنظیمات از .env)
├── requirements.txt       وابستگی‌های اجرای سایت
├── requirements-dev.txt   ابزارهای توسعه (ruff، paramiko)
├── pyproject.toml         تنظیمات lint
└── .env.example       نمونه‌ی تنظیمات محیطی
```

## راه‌اندازی محلی (توسعه)

```bash
python -m venv .venv
.venv\Scripts\activate            # ویندوز
pip install -r requirements.txt
copy .env.example .env            # و در صورت نیاز ویرایش کنید (DB_ENGINE=sqlite)
python manage.py migrate
python manage.py seed_products    # وارد کردن محصولات از _legacy/
python manage.py createsuperuser --phone 09120000000
python manage.py runserver
```

- سایت: http://127.0.0.1:8000
- پنل مدیریت: http://127.0.0.1:8000/admin/

> روی ویندوز اگر خروجی فارسی دستورها خطای encoding داد، قبلش `set PYTHONUTF8=1`.

## آدرس‌ها

| مسیر | توضیح |
|------|-------|
| `/` | صفحه‌ی اصلی + بخش هر دسته |
| `/products/?q=...` | همه محصولات + جستجو |
| `/category/<slug>/` | محصولات یک دسته |
| `/product/<slug>/` | جزئیات محصول |
| `/cart/` `/checkout/` | سبد خرید و ثبت سفارش |
| `/auth/login/` | ورود و ثبت‌نام |
| `/accounts/profile/` | حساب کاربری و سفارش‌ها |
| `/admin/` | پنل مدیریت |

## استقرار روی هاست با MySQL (phpMyAdmin)

۱. در phpMyAdmin یک دیتابیس با charset **utf8mb4** بسازید (مثلاً `hamidix`).

۲. فایل `.env` را روی هاست بسازید:

```env
SECRET_KEY=یک-رشته-تصادفی-بلند
DEBUG=False
ALLOWED_HOSTS=hamidix.ir,www.hamidix.ir
CSRF_TRUSTED_ORIGINS=https://hamidix.ir,https://www.hamidix.ir

DB_ENGINE=mysql
DB_NAME=hamidix
DB_USER=نام-کاربری-دیتابیس
DB_PASSWORD=رمز-دیتابیس
DB_HOST=localhost
DB_PORT=3306
```

۳. روی هاست:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_products      # اگر می‌خواهید محصولات اولیه وارد شوند
python manage.py createsuperuser --phone 09120000000
python manage.py collectstatic --noinput
```

۴. سرویس را با WSGI اجرا کنید (Passenger/Gunicorn). نقطه‌ی ورود: `config.wsgi:application`.

> فایل‌های استاتیک با **WhiteNoise** سرو می‌شوند، پس نیازی به تنظیم وب‌سرور جدا
> برای استاتیک نیست؛ فقط `collectstatic` را اجرا کنید. تصاویر آپلودی در `media/`
> ذخیره می‌شوند و باید توسط وب‌سرور روی `MEDIA_URL` سرو شوند.

## تست و کیفیت کد

```bash
pip install -r requirements-dev.txt
ruff check .                  # بررسی استاندارد کد
python manage.py test         # اجرای تست‌ها
```

این دو دستور در GitHub Actions روی هر push و pull request اجرا می‌شوند
(`.github/workflows/ci.yml`).

## درگاه پرداخت

ویوهای سفارش به درگاه خاصی وابسته نیستند. ماژول درگاه با تنظیم `PAYMENT_GATEWAY`
(مسیر ماژول پایتون) انتخاب می‌شود و باید سه تابع `payment_request`،
`payment_verify` و `gateway_url` را داشته باشد. جزئیات این قرارداد در
`orders/payments.py` آمده و نمونه‌ی ساده‌ی آن در `orders/tests/fake_gateway.py` است.
برای افزودن درگاه جدید کافی است یک ماژول با همین توابع بسازید و مسیرش را در `.env` بگذارید.

## تنظیمات فروشگاه

اطلاعات اختصاصی فروشگاه در مخزن ذخیره نمی‌شود و فقط از فایل `.env` خوانده می‌شود:

| متغیر | توضیح |
|-------|-------|
| `STORE_PHONE`، `STORE_ADDRESS` | شماره تماس و نشانی فروشگاه |
| `STORE_TELEGRAM_SUPPORT`، `STORE_TELEGRAM_CHANNEL`، `STORE_BALE`، `STORE_RUBIKA`، `STORE_INSTAGRAM` | شناسه‌ی شبکه‌های اجتماعی (بدون @) |
| `ENAMAD_ID`، `ENAMAD_CODE` | اطلاعات نماد اعتماد الکترونیکی |
| `PAYMENT_GATEWAY` | مسیر ماژول درگاه پرداخت |
| `ZARINPAL_MERCHANT_ID` | کد پذیرنده‌ی درگاه پرداخت |
| `DEPLOY_*` | اطلاعات اتصال سرور برای `deploy.py` |

هر مقداری که خالی بماند در سایت نمایش داده نمی‌شود.

## نکات

- درایور MySQL پیش‌فرض **PyMySQL** است (بدون نیاز به کامپایل، مناسب اشتراکی).
- ورود کاربران با **شماره تلفن** (۰۹...) و رمز هش‌شده انجام می‌شود.
- مدیریت محصولات/سفارش‌ها/کاربران از پنل ادمین جنگو انجام می‌شود.
