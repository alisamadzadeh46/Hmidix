"""
Django settings for the Hamidix shop project.

Configuration is driven by environment variables (loaded from a .env file in
development) so the same code runs on SQLite locally and MySQL on the host.
"""

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from a .env file if present.
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    """Read a boolean flag from the environment (1/true/yes/on are truthy)."""
    return os.environ.get(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


def env_str(name, default=''):
    """Read a string from the environment with surrounding whitespace removed."""
    return os.environ.get(name, default).strip()


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DEBUG', True)

# SECURITY WARNING: keep the secret key used in production secret!
# A throwaway key is allowed only for local development.
SECRET_KEY = env_str('SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG is off.')
    SECRET_KEY = 'django-insecure-local-development-only'

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Local apps
    'shop',
    'accounts',
    'orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'config.middleware.SecurityHeadersMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'orders.context_processors.cart',
                'shop.context_processors.navigation',
                'shop.context_processors.store_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# Uses MySQL when DB_ENGINE=mysql (host); falls back to SQLite for local dev.

if os.environ.get('DB_ENGINE', 'sqlite') == 'mysql':
    import pymysql

    pymysql.install_as_MySQLdb()
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'hamidix'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Custom user model (phone-number based authentication)
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.PhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'shop:home'
LOGOUT_REDIRECT_URL = 'shop:home'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

PASSWORD_RESET_TIMEOUT = 1800  # 30 minutes


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]


# Internationalization

LANGUAGE_CODE = 'fa'

TIME_ZONE = 'Asia/Tehran'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
# The hashed manifest storage requires `collectstatic`, so the test runner
# falls back to plain storage and needs no build step.
TESTING = sys.argv[1:2] == ['test']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage' if TESTING
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

# Media files (uploaded product images)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email (password reset)
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 465))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', False)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', True)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Hamidix <noreply@hamidix.ir>')

# Payment gateway: dotted path of the module implementing the interface
# documented in orders/payments.py. Credentials are provided per deployment.
PAYMENT_GATEWAY = env_str('PAYMENT_GATEWAY', 'orders.zarinpal')
ZARINPAL_MERCHANT_ID = env_str('ZARINPAL_MERCHANT_ID')
ZARINPAL_SANDBOX = env_bool('ZARINPAL_SANDBOX', True)
SITE_URL = env_str('SITE_URL').rstrip('/')

# Public store details (phone, address, social handles) and the e-Namad trust
# seal are business data, so they come from the environment as well. Any value
# left empty is simply not rendered by the templates.
STORE_CONTACT = {
    'phone': env_str('STORE_PHONE'),
    'address': env_str('STORE_ADDRESS'),
    'telegram_support': env_str('STORE_TELEGRAM_SUPPORT'),
    'telegram_channel': env_str('STORE_TELEGRAM_CHANNEL'),
    'bale': env_str('STORE_BALE'),
    'rubika': env_str('STORE_RUBIKA'),
    'instagram': env_str('STORE_INSTAGRAM'),
}
ENAMAD_ID = env_str('ENAMAD_ID')
ENAMAD_CODE = env_str('ENAMAD_CODE')

# Production security (enabled when DEBUG is off)
if not DEBUG:
    # SSL redirect stays off by default: ArvanCloud already forces HTTPS at the
    # edge, and doing it here as well would cause a redirect loop.
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
    SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', True)
    CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', True)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # The JS reads the CSRF token from the <meta> tag, so the cookie itself can
    # stay out of reach of scripts.
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True

    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    X_FRAME_OPTIONS = 'DENY'

    # HSTS: start conservative (1 day) so a certificate problem cannot lock
    # visitors out for long. Raise once HTTPS has been stable for a while.
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 86400))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
    SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', False)
