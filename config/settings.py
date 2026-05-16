# config/settings.py
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY    = os.environ.get('SECRET_KEY')
DEBUG         = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

CSRF_TRUSTED_ORIGINS = ['https://web-production-a6fe2.up.railway.app']

REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

CELERY_BROKER_URL         = REDIS_URL
CELERY_RESULT_BACKEND     = REDIS_URL
CELERY_ACCEPT_CONTENT     = ['json']
CELERY_TASK_SERIALIZER    = 'json'
CELERY_RESULT_SERIALIZER  = 'json'
CELERY_TIMEZONE           = 'Asia/Tashkent'
CELERY_TASK_TRACK_STARTED = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'refresh-mv-every-10min': {
        'task':     'dashboard.refresh_materialized_views',
        'schedule': crontab(minute='*/10'),
    },
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # ── Notebook ─────────────────────────────────────────────────────────────
    'notebook.accounts',
    'notebook.company',
    'notebook.catalog',
    'notebook.inventory',
    'notebook.clients',
    'notebook.sales',
    'notebook.payments',
    'notebook.activity',
    'notebook.dashboard',
    # ── Third-party ──────────────────────────────────────────────────────────
    'django_celery_beat',
    'django_celery_results',
    'django_resized',
]

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
ROOT_URLCONF        = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.environ.get('DB_NAME'),
        'USER':     os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST':     os.environ.get('DB_HOST', 'localhost'),
        'PORT':     os.environ.get('DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

SECURE_PROXY_SSL_HEADER  = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE    = True
CSRF_COOKIE_SECURE       = True

# ── Til va vaqt ──────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'uz'           # default: O'zbek lotin
TIME_ZONE     = 'Asia/Tashkent'
USE_I18N      = True
USE_L10N      = True
USE_TZ        = True

LANGUAGES = [
    ('uz',      "O'zbek (Lotin)"),
    ('uz-Cyrl', "O'zbek (Kirill)"),
    ('ru',      'Русский'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATIC_URL       = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL        = '/media/'
MEDIA_ROOT       = BASE_DIR / 'media'

# ── Fayl yuklanish limiti (413 xatolikni oldini olish) ───────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB (default 2.5MB edi)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB

# ── django-resized sozlamalari ────────────────────────────────────────────────
DJANGORESIZED_DEFAULT_SIZE              = [756, 741]    # product rasmiga mos
DJANGORESIZED_DEFAULT_QUALITY          = 85             # 90 o'rniga 85 — hajmni kamaytiradi
DJANGORESIZED_DEFAULT_KEEP_META        = False          # meta ma'lumotlarni o'chirish — hajm kamayadi
DJANGORESIZED_DEFAULT_FORCE_FORMAT     = 'JPEG'
DJANGORESIZED_DEFAULT_FORMAT_EXTENSIONS = {'JPEG': '.jpg'}
DJANGORESIZED_DEFAULT_NORMALIZE_ROTATION = True
