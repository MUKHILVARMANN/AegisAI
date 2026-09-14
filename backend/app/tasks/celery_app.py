"""AegisAI — Celery App Configuration."""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "aegisai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.ingestion_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,           # Ack after task completes (not on receipt)
    worker_prefetch_multiplier=1,  # One task at a time per worker
    task_max_retries=3,
    task_default_retry_delay=30,   # 30s between retries
)
