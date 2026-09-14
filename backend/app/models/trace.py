"""AegisAI — Request Trace model (full pipeline observability)."""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer, Float, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Trace(Base):
    """
    Captures every stage of a single query pipeline run.
    Used for the Trace Viewer UI and for diagnosing failures.
    """
    __tablename__ = "traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Query
    query: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Routing
    route: Mapped[str] = mapped_column(String(64), nullable=True)   # "retrieve" | "sql" | "summarize" | "workflow"
    routing_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    routing_latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    # Retrieval
    retrieval_latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    retrieved_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)
    retrieved_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    reranker_latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    final_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)

    # Generation
    model: Mapped[str] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    generation_latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=True)

    # Validation
    validation_passed: Mapped[bool] = mapped_column(nullable=True)
    validation_errors: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[str] = mapped_column(String(16), nullable=True)   # "high" | "medium" | "low"

    # Totals
    total_latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
