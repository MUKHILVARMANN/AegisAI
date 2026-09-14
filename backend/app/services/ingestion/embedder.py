"""
AegisAI — Embedder
Generates dense vector embeddings using sentence-transformers.
Singleton model loaded once, batch processing for efficiency.
"""
import logging
from functools import lru_cache

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model():
    """Load and cache the embedding model (loaded once on first call)."""
    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading embedding model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)
    logger.info("Embedding model loaded.")
    return model


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Embed a list of texts in batches.
    Returns a list of float vectors (one per input text).
    """
    if not texts:
        return []

    model = _get_model()
    logger.debug(f"Embedding {len(texts)} texts in batches of {batch_size}")

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,   # L2-normalize for cosine similarity
        convert_to_numpy=True,
    )

    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single query string. Returns a float vector."""
    result = embed_texts([query])
    return result[0] if result else []
