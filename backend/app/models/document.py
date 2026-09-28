"""AegisAI — Document & DocumentSection models."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentStatus(str, PyEnum):
    uploaded = "uploaded"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"


class DocumentType(str, PyEnum):
    pdf = "pdf"
    docx = "docx"
    xlsx = "xlsx"
    csv = "csv"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.uploaded, nullable=False
    )
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=True)
    page_count: Mapped[int] = mapped_column(nullable=True)
    chunk_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sections: Mapped[list["DocumentSection"]] = relationship(back_populates="document", cascade="all, delete")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Document id={self.id} name={self.name!r} status={self.status}>"


class DocumentSection(Base):
    __tablename__ = "document_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    heading: Mapped[str] = mapped_column(String(512), nullable=True)
    page_start: Mapped[int] = mapped_column(nullable=True)
    page_end: Mapped[int] = mapped_column(nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="sections")
