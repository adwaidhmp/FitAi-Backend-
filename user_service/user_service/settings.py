import os
from datetime import timedelta
from pathlib import Path

from decouple import config
from kombu import Queue

from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-7-r#g^cz$2)41%dml%1mvo)s9cwp9i0hhm!3fska!%paqzz@&4"
DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "user_app",
    "channels",
    "chat",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# -------------------------------------------------------------------

SIMPLE_JWT = {
    "ALGORITHM": "HS256",
    "SIGNING_KEY": config("JWT_SIGNING_KEY"),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),  # short lived
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "user_service.common.auth.SimpleJWTAuth",
    ],
}


# -------------------------------------------------------------------
# CORS settings
# -------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = "user_service.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "user_service.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"

USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
TRAINER_SERVICE_URL = os.getenv("TRAINER_SERVICE_URL")
AI_SERVICE_BASE_URL = os.getenv("AI_SERVICE_BASE_URL")

CELERY_BROKER_URL = os.getenv("RABBIT_URL")

# CELERY CONF

CELERY_TASK_DEFAULT_QUEUE = "user_tasks"

CELERY_TASK_QUEUES = (Queue("user_tasks"),)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

CELERY_TIMEZONE = TIME_ZONE

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

WSGI_APPLICATION = "user_service.wsgi.application"
ASGI_APPLICATION = "user_service.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
        },
    },
}


RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")


CELERY_BEAT_SCHEDULE = {
    "expire-premium-users-daily": {
        "task": "user.tasks.handle_expired_premium_users",
        "schedule": crontab(hour=0, minute=5),  # daily
    },
}

AWS_REGION = os.getenv("AWS_REGION")
AWS_PREMIUM_EXPIRED_QUEUE_URL = os.getenv("AWS_PREMIUM_EXPIRED_QUEUE_URL")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY= os.getenv("AWS_SECRET_ACCESS_KEY")