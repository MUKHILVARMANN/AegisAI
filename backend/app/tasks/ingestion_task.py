"""
AegisAI — Async Ingestion Task (Celery)
Processes uploaded documents: parse → chunk → embed → store.

Design principles from the blueprint:
- Idempotent: checksum dedup prevents duplicate indexing
- Status tracking: uploaded → processing → indexed | failed
- Retries: up to 3 retries with 30s backoff on failure
- Async ingestion: never blocks the API upload endpoint
"""
import hashlib
import logging
import uuid
from typing import Any

from celery import shared_task
from minio import Minio
from minio.error import S3Error
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)


def _get_sync_db() -> Session:
    """Create a synchronous SQLAlchemy session for use in Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _download_file(client: Minio, object_name: str) -> bytes:
    """Download file bytes from MinIO."""
    response = client.get_object(settings.minio_bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


@shared_task(
    bind=True,
    name="aegisai.ingest_document",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def ingest_document_task(self, document_id: str, storage_path: str, doc_type: str) -> dict[str, Any]:
    """
    Celery task: process a single document through the full ingestion pipeline.

    Steps:
    1. Update status → processing
    2. Download from MinIO
    3. Parse (text + tables + metadata)
    4. Hierarchical chunking
    5. Batch embed child chunks
    6. Store chunks + embeddings in PostgreSQL
    7. Update status → indexed
    """
    from app.models.document import Document, DocumentStatus
    from app.models.chunk import Chunk
    from app.services.ingestion.parser import parse_document
    from app.services.ingestion.chunker import chunk_document
    from app.services.ingestion.embedder import embed_texts

    db = _get_sync_db()
    doc_uuid = uuid.UUID(document_id)

    try:
        # ── 1. Fetch document record ────────────────────────────────────────
        doc = db.get(Document, doc_uuid)
        if not doc:
            logger.error(f"Document {document_id} not found in DB")
            return {"status": "error", "reason": "document not found"}

        # ── 2. Update status → processing ──────────────────────────────────
        doc.status = DocumentStatus.processing
        db.commit()
        logger.info(f"[{document_id}] Status → processing")

        # ── 3. Download from MinIO ──────────────────────────────────────────
        minio_client = _get_minio_client()
        file_bytes = _download_file(minio_client, storage_path)
        logger.info(f"[{document_id}] Downloaded {len(file_bytes)} bytes from MinIO")

        # ── 4. Parse document ───────────────────────────────────────────────
        parsed = parse_document(file_bytes, doc_type)
        doc.page_count = parsed.page_count
        logger.info(f"[{document_id}] Parsed {len(parsed.sections)} sections")

        # ── 5. Hierarchical chunking ────────────────────────────────────────
        chunk_data_list = chunk_document(doc_uuid, parsed.sections)
        child_chunks = [c for c in chunk_data_list if not c.is_parent]
        parent_chunks = [c for c in chunk_data_list if c.is_parent]
        logger.info(f"[{document_id}] Created {len(parent_chunks)} parent + {len(child_chunks)} child chunks")

        # ── 6. Embed child chunks (batch) ───────────────────────────────────
        child_texts = [c.text for c in child_chunks]
        embeddings = embed_texts(child_texts, batch_size=64)
        logger.info(f"[{document_id}] Generated {len(embeddings)} embeddings")

        # ── 7. Store all chunks ─────────────────────────────────────────────
        # Delete existing chunks first (idempotency — re-ingestion support)
        from sqlalchemy import delete
        db.execute(delete(Chunk).where(Chunk.document_id == doc_uuid))

        # Insert parent chunks (no embedding)
        for pc in parent_chunks:
            db.add(Chunk(
                id=pc.id,
                document_id=pc.document_id,
                section_id=pc.section_id,
                parent_chunk_id=pc.parent_chunk_id,
                text=pc.text,
                is_parent=True,
                page_number=pc.page_number,
                heading=pc.heading,
                source_type=pc.source_type,
                chunk_index=pc.chunk_index,
                extra_metadata=pc.extra_metadata,
                embedding=None,
            ))

        # Insert child chunks with embeddings
        for cc, emb in zip(child_chunks, embeddings):
            db.add(Chunk(
                id=cc.id,
                document_id=cc.document_id,
                section_id=cc.section_id,
                parent_chunk_id=cc.parent_chunk_id,
                text=cc.text,
                is_parent=False,
                page_number=cc.page_number,
                heading=cc.heading,
                source_type=cc.source_type,
                chunk_index=cc.chunk_index,
                extra_metadata=cc.extra_metadata,
                embedding=emb,
            ))

        # ── 8. Update document status → indexed ────────────────────────────
        doc.chunk_count = len(chunk_data_list)
        doc.status = DocumentStatus.indexed
        db.commit()

        logger.info(f"[{document_id}] Status → indexed. Ingestion complete.")
        return {
            "status": "indexed",
            "document_id": document_id,
            "chunks": len(chunk_data_list),
        }

    except Exception as exc:
        logger.exception(f"[{document_id}] Ingestion failed: {exc}")

        # Mark document as failed with error message
        try:
            doc = db.get(Document, doc_uuid)
            if doc:
                from app.models.document import DocumentStatus
                doc.status = DocumentStatus.failed
                doc.error_message = str(exc)[:1000]
                db.commit()
        except Exception:
            pass

        # Retry with backoff
        raise self.retry(exc=exc)

    finally:
        db.close()
