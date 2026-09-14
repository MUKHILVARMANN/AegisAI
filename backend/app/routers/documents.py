"""
AegisAI — Documents Router
POST /documents       — upload a document
GET  /documents       — list all documents
GET  /documents/{id}  — get document status + metadata
POST /documents/{id}/reprocess — re-trigger ingestion
"""
import hashlib
import io
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.document import Document, DocumentStatus, DocumentType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/csv": "csv",
    "application/octet-stream": None,  # will infer from filename
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def _get_doc_type(filename: str, content_type: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in {"pdf", "docx", "xlsx", "csv"}:
        return ext
    ct_type = ALLOWED_CONTENT_TYPES.get(content_type)
    if ct_type:
        return ct_type
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename!r}")


def _get_minio() -> Minio:
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    # Ensure bucket exists
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
    return client


class DocumentResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    page_count: int | None
    chunk_count: int
    created_at: str

    class Config:
        from_attributes = True


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for async ingestion.
    Returns immediately with document ID. Ingestion happens in background.
    """
    # ── Validate ─────────────────────────────────────────────────────────
    doc_type = _get_doc_type(file.filename or "unknown", file.content_type or "")
    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")

    # ── Checksum for dedup ────────────────────────────────────────────────
    checksum = hashlib.sha256(file_bytes).hexdigest()
    existing = await db.execute(select(Document).where(Document.checksum == checksum))
    existing_doc = existing.scalar_one_or_none()
    if existing_doc:
        return {
            "document_id": str(existing_doc.id),
            "status": existing_doc.status,
            "message": "Document already exists (checksum match). Use /reprocess to re-index.",
        }

    # ── Create DB record ──────────────────────────────────────────────────
    doc_id = uuid.uuid4()
    storage_path = f"{doc_id}/{file.filename}"

    doc = Document(
        id=doc_id,
        name=file.filename or "unknown",
        type=DocumentType(doc_type),
        status=DocumentStatus.uploaded,
        checksum=checksum,
        storage_path=storage_path,
    )
    db.add(doc)
    await db.commit()

    # ── Upload to MinIO ───────────────────────────────────────────────────
    try:
        minio_client = _get_minio()
        minio_client.put_object(
            settings.minio_bucket,
            storage_path,
            io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=file.content_type or "application/octet-stream",
        )
    except S3Error as e:
        doc.status = DocumentStatus.failed
        doc.error_message = f"MinIO upload failed: {e}"
        await db.commit()
        raise HTTPException(status_code=500, detail="File storage failed")

    # ── Queue ingestion task ──────────────────────────────────────────────
    from app.tasks.ingestion_task import ingest_document_task
    ingest_document_task.delay(str(doc_id), storage_path, doc_type)

    logger.info(f"Document {doc_id} uploaded, ingestion queued")

    return {
        "document_id": str(doc_id),
        "status": DocumentStatus.uploaded,
        "message": "Document uploaded. Ingestion queued.",
    }


@router.get("", response_model=list[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all documents with their ingestion status."""
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=str(d.id),
            name=d.name,
            type=d.type.value,
            status=d.status.value,
            page_count=d.page_count,
            chunk_count=d.chunk_count or 0,
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single document's status and metadata."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = await db.get(Document, doc_uuid)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=str(doc.id),
        name=doc.name,
        type=doc.type.value,
        status=doc.status.value,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count or 0,
        created_at=doc.created_at.isoformat(),
    )


@router.post("/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Re-trigger ingestion for an existing document (e.g. after failure)."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = await db.get(Document, doc_uuid)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = DocumentStatus.uploaded
    doc.error_message = None
    await db.commit()

    from app.tasks.ingestion_task import ingest_document_task
    ingest_document_task.delay(str(doc.id), doc.storage_path, doc.type.value)

    return {"document_id": document_id, "status": "reprocessing", "message": "Re-ingestion queued."}
