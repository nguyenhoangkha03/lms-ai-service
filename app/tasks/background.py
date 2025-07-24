from celery import Celery
from app.config.settings import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "ai-services",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.analytics",
        "app.tasks.ml_training",
        "app.tasks.notifications"
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.analytics.*": {"queue": "analytics"},
    "app.tasks.ml_training.*": {"queue": "ml_training"},
    "app.tasks.notifications.*": {"queue": "notifications"},
}

@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing"""
    print(f"Request: {self.request!r}")
    return "Task completed successfully"