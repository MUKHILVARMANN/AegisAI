"""
AegisAI — Vector Search
Dense retrieval using pgvector cosine similarity.
Returns the top-N most similar child chunks for a query embedding.
"""
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchResult:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    text: str
    score: float            # cosine similarity 0-1
    page_number: int | None
    heading: str | None
    source_type: str
    parent_chunk_id: uuid.UUID | None
    is_parent: bool


async def vector_search(
    db: AsyncSession,
    query_embedding: list[float],
    top_n: int | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> list[VectorSearchResult]:
    """
    Perform cosine similarity search using pgvector.
    Retrieves only CHILD chunks (is_parent=False) for precision.
    Filters by document_ids if provided.
    """
    top_n = top_n or settings.retrieval_top_n

    # Build dynamic filter clause
    doc_filter = ""
    params: dict = {
        "embedding": str(query_embedding),
        "top_n": top_n,
    }

    if document_ids:
        doc_filter = "AND c.document_id = ANY(:doc_ids)"
        params["doc_ids"] = [str(did) for did in document_ids]

    sql = text(f"""
        SELECT
            c.id::text                  AS chunk_id,
            c.document_id::text         AS document_id,
            c.text                      AS text,
            1 - (c.embedding <=> :embedding::vector) AS score,
            c.page_number,
            c.heading,
            c.source_type,
            c.parent_chunk_id::text     AS parent_chunk_id,
            c.is_parent
        FROM chunks c
        WHERE c.is_parent = false
          AND c.embedding IS NOT NULL
          {doc_filter}
        ORDER BY c.embedding <=> :embedding::vector
        LIMIT :top_n
    """)

    rows = await db.execute(sql, params)
    results = rows.fetchall()

    return [
        VectorSearchResult(
            chunk_id=uuid.UUID(r.chunk_id),
            document_id=uuid.UUID(r.document_id),
            text=r.text,
            score=float(r.score),
            page_number=r.page_number,
            heading=r.heading,
            source_type=r.source_type,
            parent_chunk_id=uuid.UUID(r.parent_chunk_id) if r.parent_chunk_id else None,
            is_parent=r.is_parent,
        )
        for r in results
    ]
