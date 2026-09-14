"""AegisAI — Traces Router. GET /traces/{request_id}"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.trace import Trace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("/{request_id}")
async def get_trace(request_id: str, db: AsyncSession = Depends(get_db)):
    """Get a full pipeline trace by request_id. Used by the Trace Viewer UI."""
    result = await db.execute(select(Trace).where(Trace.request_id == request_id))
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    return {
        "request_id": trace.request_id,
        "query": trace.query,
        "pipeline_stages": [
            {
                "stage": "intent_routing",
                "route": trace.route,
                "confidence": trace.routing_confidence,
                "latency_ms": trace.routing_latency_ms,
            },
            {
                "stage": "retrieval",
                "chunk_count": len(trace.retrieved_chunk_ids or []),
                "chunk_ids": trace.retrieved_chunk_ids,
                "scores": trace.retrieved_scores,
                "latency_ms": trace.retrieval_latency_ms,
            },
            {
                "stage": "reranking",
                "final_chunks": trace.final_chunk_ids,
                "latency_ms": trace.reranker_latency_ms,
            },
            {
                "stage": "generation",
                "model": trace.model,
                "prompt_version": trace.prompt_version,
                "input_tokens": trace.input_tokens,
                "output_tokens": trace.output_tokens,
                "latency_ms": trace.generation_latency_ms,
                "estimated_cost_usd": trace.estimated_cost_usd,
            },
            {
                "stage": "validation",
                "passed": trace.validation_passed,
                "errors": trace.validation_errors,
                "confidence": trace.confidence,
            },
        ],
        "total_latency_ms": trace.total_latency_ms,
        "created_at": trace.created_at.isoformat(),
    }


@router.get("")
async def list_traces(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """List recent traces."""
    result = await db.execute(
        select(Trace).order_by(Trace.created_at.desc()).limit(limit)
    )
    traces = result.scalars().all()
    return [
        {
            "request_id": t.request_id,
            "query": t.query[:100] + "..." if len(t.query) > 100 else t.query,
            "route": t.route,
            "total_latency_ms": t.total_latency_ms,
            "confidence": t.confidence,
            "validation_passed": t.validation_passed,
            "created_at": t.created_at.isoformat(),
        }
        for t in traces
    ]
