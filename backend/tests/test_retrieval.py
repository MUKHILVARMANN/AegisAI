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


def compute_recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Compute Recall@K = |Retrieved@K ∩ Relevant| / |Relevant|"""
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for cid in top_k if cid in relevant_ids)
    return hits / len(relevant_ids)


def compute_mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Compute Mean Reciprocal Rank (MRR) = 1 / first_relevant_rank"""
    for rank, cid in enumerate(retrieved_ids, start=1):
        if cid in relevant_ids:
            return 1.0 / rank
    return 0.0


class TestRetrievalBenchmark:
    """Retrieval benchmark evaluating Recall@K and MRR for dense, sparse, and hybrid search."""

    def test_recall_at_k_calculation(self):
        relevant = {"c1", "c2"}
        retrieved = ["c3", "c1", "c4", "c2", "c5"]

        assert compute_recall_at_k(retrieved, relevant, k=1) == 0.0
        assert compute_recall_at_k(retrieved, relevant, k=2) == 0.5  # c1 found
        assert compute_recall_at_k(retrieved, relevant, k=4) == 1.0  # c1 and c2 found

    def test_mrr_calculation(self):
        relevant = {"target"}
        assert compute_mrr(["target", "other"], relevant) == 1.0
        assert compute_mrr(["other", "target"], relevant) == 0.5
        assert compute_mrr(["other", "other2", "target"], relevant) == pytest.approx(1.0 / 3)
        assert compute_mrr(["other1", "other2"], relevant) == 0.0

    def test_hybrid_improves_or_matches_mrr_over_single_modality(self):
        """
        Scenario: Query with both keyword entity (favoring BM25) and conceptual match (favoring vector).
        Relevant target: chunk-1.
        Vector rank for chunk-1: #3
        BM25 rank for chunk-1: #2
        Hybrid RRF: chunk-1 is elevated to #1 due to reciprocal rank summation.
        """
        relevant = {str(uuid.UUID(int=1))}

        vector = [_v(2, 0.95), _v(3, 0.90), _v(1, 0.85)]
        bm25 = [_b(4, 0.92), _b(1, 0.88), _b(5, 0.80)]

        v_ids = [str(r.chunk_id) for r in vector]
        b_ids = [r.chunk_id for r in bm25]

        mrr_vector = compute_mrr(v_ids, relevant)  # 1/3 ≈ 0.333
        mrr_bm25 = compute_mrr(b_ids, relevant)    # 1/2 = 0.5

        fused = _reciprocal_rank_fusion(vector, bm25)
        fused_ids = [r.chunk_id for r in fused]
        mrr_hybrid = compute_mrr(fused_ids, relevant)

        # Chunk 1 appears in both, elevating it to rank 1 in hybrid
        assert fused_ids[0] == str(uuid.UUID(int=1))
        assert mrr_hybrid == 1.0
        assert mrr_hybrid > mrr_vector
        assert mrr_hybrid > mrr_bm25

