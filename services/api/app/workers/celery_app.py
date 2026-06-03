"""Celery application configuration."""
from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "fashion_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    result_expires=3600,

    # Retry
    task_default_retry_delay=30,
    task_max_retries=3,

    # Queues
    task_routes={
        "app.workers.tasks.reconstruct_body_task": {"queue": "ml"},
        "app.workers.tasks.generate_outfit_task": {"queue": "ml"},
        "app.workers.tasks.virtual_tryon_task": {"queue": "ml"},
        "app.workers.tasks.ingest_products_task": {"queue": "default"},
        "app.workers.tasks.retrain_model_task": {"queue": "ml"},
        "app.workers.tasks.cleanup_old_data_task": {"queue": "default"},
    },

    # Beat schedule (periodic tasks)
    beat_schedule={
        "cleanup-old-data-daily": {
            "task": "app.workers.tasks.cleanup_old_data_task",
            "schedule": 86400.0,  # 24 hours
        },
        "health-ping-10min": {
            "task": "app.workers.tasks.health_ping_task",
            "schedule": 600.0,  # 10 minutes — prevent Render sleep
        },
    },
)
