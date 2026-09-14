"""
AegisAI — FastAPI Application Entry Point
Production-grade AI Knowledge & Decision Platform
"""
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.database import init_db
from app.routers import documents, chat, traces, feedback, evaluations, health

# ─── Logging ─────────────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = structlog.get_logger()


# ─── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)


# ─── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB tables. Shutdown: cleanup."""
    logger.info("AegisAI starting up...")
    await init_db()
    logger.info("Database initialized (tables created, pgvector extension enabled)")

    # Ensure MinIO bucket exists
    try:
        from minio import Minio
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
            logger.info(f"MinIO bucket '{settings.minio_bucket}' created")
    except Exception as e:
        logger.warning(f"MinIO initialization warning: {e}")

    yield
    logger.info("AegisAI shutting down.")


# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AegisAI",
    description="Production-Grade AI Knowledge & Decision Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with method, path, and status."""
    import time
    t0 = time.perf_counter()
    response = await call_next(request)
    latency = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=latency,
    )
    return response


# ─── Error Handlers ───────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(traces.router)
app.include_router(feedback.router)
app.include_router(evaluations.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "name": "AegisAI",
        "description": "Production-Grade AI Knowledge & Decision Platform",
        "version": "1.0.0",
        "docs": "/docs",
    }
