import os
import ssl

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")

app = Celery("auth_service")

# Load Django settings (CELERY_*)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Force SSL options for Redis (Upstash)
app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

app.autodiscover_tasks()
