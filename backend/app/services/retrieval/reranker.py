"""
AegisAI — Cross-Encoder Reranker
Uses a cross-encoder model to rerank top-N hybrid search candidates to top-K.

Why cross-encoder vs bi-encoder?
- Cross-encoders jointly encode query+passage, giving much higher relevance accuracy
- Too slow to run on the entire corpus (use hybrid search for candidate generation first)
- Applied only to the top-N candidates from hybrid search
"""
import logging
import time
from functools import lru_cache

from app.config import settings
from app.services.retrieval.hybrid_search import HybridSearchResult

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_reranker():
    """Load cross-encoder model once, cache it."""
    from sentence_transformers import CrossEncoder
    logger.info(f"Loading reranker model: {settings.reranker_model}")
    model = CrossEncoder(settings.reranker_model, max_length=512)
    logger.info("Reranker loaded.")
    return model


def rerank(
    query: str,
    candidates: list[HybridSearchResult],
    top_k: int | None = None,
) -> tuple[list[HybridSearchResult], int]:
    """
    Rerank candidates using cross-encoder scores.
    Returns (reranked_top_k, latency_ms).
    """
    top_k = top_k or settings.reranker_top_k

    if not candidates:
        return [], 0

    t0 = time.perf_counter()
    model = _get_reranker()

    # Prepare query-passage pairs
    pairs = [(query, c.text) for c in candidates]

    # Cross-encoder inference
    scores = model.predict(pairs, show_progress_bar=False)

    latency_ms = int((time.perf_counter() - t0) * 1000)

    # Attach reranker scores and sort
    scored = sorted(
        zip(scores.tolist(), candidates),
        key=lambda x: x[0],
        reverse=True,
    )

    # Keep top-K
    reranked = []
    for score, candidate in scored[:top_k]:
        candidate.rrf_score = float(score)   # overwrite rrf_score with reranker score
        reranked.append(candidate)

    logger.info(
        f"Reranker: {len(candidates)} → {len(reranked)} chunks | latency={latency_ms}ms"
    )

    return reranked, latency_ms
