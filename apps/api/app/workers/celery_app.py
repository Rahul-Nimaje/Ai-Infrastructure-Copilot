"""Celery application configuration.

Uses Redis as both broker and result backend (already in docker-compose).
Workers process document ingestion, re-indexing, and deletion in the background
so API requests return immediately.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ai_infra_copilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry configuration
    task_default_retry_delay=30,  # seconds
    task_max_retries=3,
    # Task routing
    task_routes={
        "app.workers.tasks.document_tasks.*": {"queue": "documents"},
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.workers.tasks"])
