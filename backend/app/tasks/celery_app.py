"""Celery application instance."""

from celery import Celery

from app.config import settings

# Initialize Celery application
celery_app = Celery("nightshift_analyst")

# Configure broker and result backend from settings
celery_app.conf.broker_url = settings.CELERY_BROKER_URL
celery_app.conf.result_backend = settings.CELERY_RESULT_BACKEND

# Eagerly import task modules to ensure registration
celery_app.autodiscover_tasks(["app"])


@celery_app.task(name="app.tasks.health_check")
def health_check() -> str:
    """Simple task used to verify Celery worker is running."""
    return "ok"
