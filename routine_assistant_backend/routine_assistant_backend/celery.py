"""Celery application configuration for the Django project."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "routine_assistant_backend.settings")

app = Celery("routine_assistant_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
