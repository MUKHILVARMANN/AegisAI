"""
AegisAI — Request Tracer
Captures every pipeline stage for observability and debugging.
Stores traces to the DB asynchronously so they don't block responses.
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PipelineTrace:
    """
    Mutable trace object built up as a request flows through the pipeline.
    Call .finalize() before saving to DB.
    """
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    query: str = ""
    conversation_id: str | None = None

    # Routing
    route: str | None = None
    routing_confidence: float | None = None
    routing_latency_ms: int | None = None

    # Retrieval
    retrieval_latency_ms: int | None = None
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    retrieved_scores: dict[str, float] = field(default_factory=dict)
    reranker_latency_ms: int | None = None
    final_chunk_ids: list[str] = field(default_factory=list)

    # Generation
    model: str | None = None
    prompt_version: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    generation_latency_ms: int | None = None
    estimated_cost_usd: float | None = None

    # Validation
    validation_passed: bool | None = None
    validation_errors: list[str] = field(default_factory=list)
    confidence: str | None = None

    # Total
    total_latency_ms: int | None = None
    _start_time: float = field(default_factory=time.perf_counter, repr=False)

    def finalize(self) -> "PipelineTrace":
        """Calculate total latency and return self."""
        self.total_latency_ms = int((time.perf_counter() - self._start_time) * 1000)
        return self

    def to_db_dict(self) -> dict:
        """Convert to dict for DB insertion."""
        return {
            "request_id": self.request_id,
            "query": self.query,
            "conversation_id": self.conversation_id,
            "route": self.route,
            "routing_confidence": self.routing_confidence,
            "routing_latency_ms": self.routing_latency_ms,
            "retrieval_latency_ms": self.retrieval_latency_ms,
            "retrieved_chunk_ids": self.retrieved_chunk_ids,
            "retrieved_scores": self.retrieved_scores,
            "reranker_latency_ms": self.reranker_latency_ms,
            "final_chunk_ids": self.final_chunk_ids,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "generation_latency_ms": self.generation_latency_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "confidence": self.confidence,
            "total_latency_ms": self.total_latency_ms,
        }


async def save_trace(db, trace: PipelineTrace) -> None:
    """Save a finalized trace to the database."""
    from app.models.trace import Trace
    db_trace = Trace(**trace.to_db_dict())
    db.add(db_trace)
    await db.commit()
    logger.debug(f"Trace saved: request_id={trace.request_id}")
