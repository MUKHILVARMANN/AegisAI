"""AegisAI — Chunk model with pgvector embedding column."""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer, JSON, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import settings


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    parent_chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_parent: Mapped[bool] = mapped_column(default=False)  # True = parent chunk (context), False = child (retrieved)

    # Metadata for filtering
    page_number: Mapped[int] = mapped_column(Integer, nullable=True)
    heading: Mapped[str] = mapped_column(String(512), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=True)   # "pdf", "table", "docx", etc.
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Vector embedding (pgvector)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="chunks")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Chunk id={self.id} doc={self.document_id} page={self.page_number}>"
