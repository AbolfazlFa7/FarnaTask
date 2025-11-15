from celery import Celery
from django.conf import settings
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.conf.enable_utc = False
app.conf.update(timezone=settings.CELERY_TIMEZONE)

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
