"""
AegisAI — Hybrid Search (Reciprocal Rank Fusion)
Fuses dense vector results and sparse BM25 results using RRF.

RRF formula: score(d) = Σ 1 / (k + rank(d))
where k=60 is a smoothing constant.

Why RRF?
- No score normalization required (rank-based, not score-based)
- Works well even when vector and BM25 score distributions differ significantly
- Simple, robust, consistently outperforms score-based fusion in benchmarks
"""
import logging
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.retrieval.vector_search import vector_search, VectorSearchResult
from app.services.retrieval.bm25_search import bm25_search, BM25SearchResult

logger = logging.getLogger(__name__)

RRF_K = 60  # Standard RRF smoothing constant


@dataclass
class HybridSearchResult:
    chunk_id: str
    document_id: str
    text: str
    rrf_score: float
    vector_score: float | None = None
    bm25_score: float | None = None
    page_number: int | None = None
    heading: str | None = None
    source_type: str = "text"
    parent_chunk_id: str | None = None
    parent_text: str | None = None     # Populated after parent context retrieval


async def _fetch_all_child_chunks(db: AsyncSession, document_ids: list[uuid.UUID] | None = None) -> list[dict]:
    """Fetch all child chunks from DB for BM25 indexing."""
    doc_filter = ""
    params: dict = {}

    if document_ids:
        doc_filter = "AND document_id = ANY(:doc_ids)"
        params["doc_ids"] = [str(did) for did in document_ids]

    sql = text(f"""
        SELECT id::text, document_id::text, text, page_number,
               heading, source_type, parent_chunk_id::text
        FROM chunks
        WHERE is_parent = false
          AND embedding IS NOT NULL
          {doc_filter}
        LIMIT 50000
    """)

    rows = await db.execute(sql, params)
    return [dict(r._mapping) for r in rows.fetchall()]


async def _fetch_parent_texts(db: AsyncSession, parent_ids: list[str]) -> dict[str, str]:
    """Fetch parent chunk texts for context injection."""
    if not parent_ids:
        return {}

    sql = text("""
        SELECT id::text, text FROM chunks
        WHERE id = ANY(:ids) AND is_parent = true
    """)
    rows = await db.execute(sql, {"ids": parent_ids})
    return {r.id: r.text for r in rows.fetchall()}


def _reciprocal_rank_fusion(
    vector_results: list[VectorSearchResult],
    bm25_results: list[BM25SearchResult],
    k: int = RRF_K,
) -> list[HybridSearchResult]:
    """Fuse two ranked lists using RRF."""
    scores: dict[str, dict] = {}

    # Process vector results
    for rank, vr in enumerate(vector_results):
        cid = str(vr.chunk_id)
        if cid not in scores:
            scores[cid] = {
                "chunk_id": cid,
                "document_id": str(vr.document_id),
                "text": vr.text,
                "rrf_score": 0.0,
                "vector_score": None,
                "bm25_score": None,
                "page_number": vr.page_number,
                "heading": vr.heading,
                "source_type": vr.source_type,
                "parent_chunk_id": str(vr.parent_chunk_id) if vr.parent_chunk_id else None,
            }
        scores[cid]["rrf_score"] += 1.0 / (k + rank + 1)
        scores[cid]["vector_score"] = vr.score

    # Process BM25 results
    for rank, br in enumerate(bm25_results):
        cid = br.chunk_id
        if cid not in scores:
            scores[cid] = {
                "chunk_id": cid,
                "document_id": br.document_id,
                "text": br.text,
                "rrf_score": 0.0,
                "vector_score": None,
                "bm25_score": None,
                "page_number": br.page_number,
                "heading": br.heading,
                "source_type": br.source_type or "text",
                "parent_chunk_id": br.parent_chunk_id,
            }
        scores[cid]["rrf_score"] += 1.0 / (k + rank + 1)
        scores[cid]["bm25_score"] = br.score

    # Sort by RRF score descending
    ranked = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)

    return [
        HybridSearchResult(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            text=r["text"],
            rrf_score=r["rrf_score"],
            vector_score=r["vector_score"],
            bm25_score=r["bm25_score"],
            page_number=r["page_number"],
            heading=r["heading"],
            source_type=r["source_type"],
            parent_chunk_id=r["parent_chunk_id"],
        )
        for r in ranked
    ]


async def hybrid_search(
    db: AsyncSession,
    query: str,
    query_embedding: list[float],
    top_n: int | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> tuple[list[HybridSearchResult], dict]:
    """
    Full hybrid search pipeline:
    1. Vector search (dense)
    2. BM25 search (sparse)
    3. RRF fusion
    4. Parent context injection for top results
    Returns (results, timing_info)
    """
    top_n = top_n or settings.retrieval_top_n
    timings: dict = {}

    # ── 1. Parallel retrieval ──────────────────────────────────────────────
    t0 = time.perf_counter()
    corpus = await _fetch_all_child_chunks(db, document_ids)
    timings["corpus_fetch_ms"] = int((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    vector_results = await vector_search(db, query_embedding, top_n, document_ids)
    timings["vector_ms"] = int((time.perf_counter() - t1) * 1000)

    t2 = time.perf_counter()
    bm25_results = await bm25_search(query, corpus, top_n)
    timings["bm25_ms"] = int((time.perf_counter() - t2) * 1000)

    # ── 2. RRF Fusion ─────────────────────────────────────────────────────
    fused = _reciprocal_rank_fusion(vector_results, bm25_results)
    top_candidates = fused[:top_n]

    # ── 3. Parent context injection ───────────────────────────────────────
    parent_ids = [c.parent_chunk_id for c in top_candidates if c.parent_chunk_id]
    parent_texts = await _fetch_parent_texts(db, parent_ids)
    for candidate in top_candidates:
        if candidate.parent_chunk_id and candidate.parent_chunk_id in parent_texts:
            candidate.parent_text = parent_texts[candidate.parent_chunk_id]

    logger.info(
        f"Hybrid search: {len(vector_results)} vector + {len(bm25_results)} bm25 → "
        f"{len(top_candidates)} candidates | timings={timings}"
    )

    return top_candidates, timings
