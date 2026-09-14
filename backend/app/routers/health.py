"""AegisAI — Health & Metrics Router. GET /health, GET /metrics"""
import time
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Liveness + readiness check for all dependencies."""
    checks = {}

    # DB check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis check
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # MinIO check
    try:
        from minio import Minio
        client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key,
                       secret_key=settings.minio_secret_key, secure=settings.minio_secure)
        client.list_buckets()
        checks["minio"] = "ok"
    except Exception as e:
        checks["minio"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
        "version": "1.0.0",
    }


@router.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_db)):
    """High-level system metrics."""
    from sqlalchemy import select, func
    from app.models.document import Document
    from app.models.trace import Trace
    from app.models.feedback import Feedback

    doc_count = (await db.execute(select(func.count()).select_from(Document))).scalar()
    trace_count = (await db.execute(select(func.count()).select_from(Trace))).scalar()
    feedback_count = (await db.execute(select(func.count()).select_from(Feedback))).scalar()

    # Avg latency from last 100 traces
    avg_latency = (await db.execute(
        select(func.avg(Trace.total_latency_ms)).select_from(Trace).order_by(Trace.created_at.desc()).limit(100)
    )).scalar()

    return {
        "documents": doc_count,
        "traces": trace_count,
        "feedback_entries": feedback_count,
        "avg_latency_ms_last_100": round(avg_latency or 0, 1),
    }
