"""Tests for hybrid search RRF fusion logic."""
import pytest

from app.services.retrieval.hybrid_search import _reciprocal_rank_fusion, HybridSearchResult
from app.services.retrieval.vector_search import VectorSearchResult
from app.services.retrieval.bm25_search import BM25SearchResult
import uuid


def _make_vector_result(chunk_id: str, score: float) -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=uuid.UUID(int=int(chunk_id.replace("c", ""), 16)) if chunk_id.startswith("c") else uuid.uuid4(),
        document_id=uuid.uuid4(),
        text=f"Text for chunk {chunk_id}",
        score=score,
        page_number=1,
        heading="Test",
        source_type="text",
        parent_chunk_id=None,
        is_parent=False,
    )


def _v(idx: int, score: float) -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=uuid.UUID(int=idx),
        document_id=uuid.UUID(int=0),
        text=f"chunk-{idx}",
        score=score,
        page_number=1,
        heading=None,
        source_type="text",
        parent_chunk_id=None,
        is_parent=False,
    )


def _b(idx: int, score: float) -> BM25SearchResult:
    return BM25SearchResult(
        chunk_id=str(uuid.UUID(int=idx)),
        document_id=str(uuid.UUID(int=0)),
        text=f"chunk-{idx}",
        score=score,
        page_number=1,
        heading=None,
        source_type="text",
        parent_chunk_id=None,
    )


class TestRRFFusion:
    def test_chunks_in_both_lists_ranked_higher(self):
        """A chunk appearing in both vector and BM25 results should rank above chunks in only one."""
        # chunk-1 in both, chunk-2 only in vector, chunk-3 only in bm25
        vector = [_v(1, 0.95), _v(2, 0.80)]
        bm25 = [_b(1, 0.90), _b(3, 0.70)]

        fused = _reciprocal_rank_fusion(vector, bm25)
        chunk_ids = [r.chunk_id for r in fused]

        assert chunk_ids[0] == str(uuid.UUID(int=1)), "Chunk-1 (in both lists) should rank first"

    def test_output_contains_all_unique_chunks(self):
        """All unique chunks from both lists should be in the fused output."""
        vector = [_v(1, 0.9), _v(2, 0.8)]
        bm25 = [_b(2, 0.7), _b(3, 0.6)]

        fused = _reciprocal_rank_fusion(vector, bm25)
        chunk_ids = {r.chunk_id for r in fused}

        # All 3 unique chunks should appear
        assert len(chunk_ids) == 3

    def test_rrf_scores_decrease_monotonically(self):
        """RRF scores should be non-increasing (sorted descending)."""
        vector = [_v(i, 1.0 - i * 0.1) for i in range(5)]
        bm25 = [_b(i + 3, 0.8 - i * 0.1) for i in range(5)]

        fused = _reciprocal_rank_fusion(vector, bm25)
        scores = [r.rrf_score for r in fused]

        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], "RRF scores should be sorted descending"

    def test_empty_lists_return_empty(self):
        """Empty inputs should return empty output."""
        assert _reciprocal_rank_fusion([], []) == []

    def test_single_list_works(self):
        """Should work with only vector results and no BM25 results."""
        vector = [_v(1, 0.9), _v(2, 0.8)]
        fused = _reciprocal_rank_fusion(vector, [])
        assert len(fused) == 2
