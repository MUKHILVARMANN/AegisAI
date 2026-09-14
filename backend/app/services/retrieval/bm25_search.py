"""
AegisAI — BM25 Keyword Search
Sparse retrieval using rank_bm25 for exact term matching.
Complements vector search for IDs, proper nouns, technical vocabulary.

BM25 indices are built on-demand from DB and cached in Redis for efficiency.
"""
import json
import logging
import uuid
from dataclasses import dataclass

import redis

from app.config import settings

logger = logging.getLogger(__name__)

# Redis client for BM25 index caching
_redis_client: redis.Redis | None = None

BM25_INDEX_TTL = 3600  # 1 hour


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


@dataclass
class BM25SearchResult:
    chunk_id: str
    document_id: str
    text: str
    score: float
    page_number: int | None
    heading: str | None
    source_type: str
    parent_chunk_id: str | None


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer."""
    return text.lower().split()


async def bm25_search(
    query: str,
    corpus: list[dict],  # list of chunk dicts: {id, document_id, text, page_number, heading, source_type, parent_chunk_id}
    top_n: int | None = None,
) -> list[BM25SearchResult]:
    """
    Run BM25 over a corpus of chunk dicts.
    corpus is the full set of child chunks from DB (pre-fetched by caller).
    Returns top_n results sorted by BM25 score descending.
    """
    from rank_bm25 import BM25Okapi

    top_n = top_n or settings.retrieval_top_n

    if not corpus:
        return []

    tokenized_corpus = [_tokenize(c["text"]) for c in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = _tokenize(query)
    scores = bm25.get_scores(tokenized_query)

    # Pair scores with chunks and sort
    scored_chunks = sorted(
        zip(scores, corpus),
        key=lambda x: x[0],
        reverse=True,
    )

    # Normalize scores to 0-1
    max_score = scored_chunks[0][0] if scored_chunks else 1.0
    if max_score == 0:
        max_score = 1.0

    results = []
    for score, chunk in scored_chunks[:top_n]:
        if score <= 0:
            break   # BM25 score of 0 = no term overlap
        results.append(BM25SearchResult(
            chunk_id=str(chunk["id"]),
            document_id=str(chunk["document_id"]),
            text=chunk["text"],
            score=float(score / max_score),
            page_number=chunk.get("page_number"),
            heading=chunk.get("heading"),
            source_type=chunk.get("source_type", "text"),
            parent_chunk_id=str(chunk["parent_chunk_id"]) if chunk.get("parent_chunk_id") else None,
        ))

    return results
