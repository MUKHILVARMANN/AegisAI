"""Tests for the citation validator."""
import pytest

from app.services.generation.llm_client import LLMResponse
from app.services.generation.validator import validate_response


def _make_response(answer="Valid answer here.", citations=None, confidence="high") -> LLMResponse:
    return LLMResponse(
        answer=answer,
        citations=citations or [],
        confidence=confidence,
        limitations=[],
        input_tokens=100,
        output_tokens=50,
        latency_ms=500,
        model="gpt-4o",
    )


class TestValidator:
    def test_valid_response_passes(self):
        """A response with valid citations should pass."""
        evidence_ids = {"chunk-001", "chunk-002", "chunk-003"}
        evidence = [{"chunk_id": cid, "document_id": "doc-1", "text": "Evidence text"} for cid in evidence_ids]

        response = _make_response(
            answer="The answer is X based on the documentation.",
            citations=[{"chunk_id": "chunk-001", "document_id": "doc-1", "page": 1, "heading": "Intro"}],
        )

        result = validate_response(response, evidence_ids, evidence)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_hallucinated_citation_detected(self):
        """Citations referencing chunk_ids not in evidence should fail."""
        evidence_ids = {"chunk-001"}
        evidence = [{"chunk_id": "chunk-001", "document_id": "doc-1", "text": "Real evidence"}]

        response = _make_response(
            answer="The answer based on my knowledge.",
            citations=[
                {"chunk_id": "chunk-001", "document_id": "doc-1", "page": 1, "heading": "OK"},
                {"chunk_id": "chunk-FAKE-999", "document_id": "doc-1", "page": 5, "heading": "FAKE"},  # hallucinated
            ],
        )

        result = validate_response(response, evidence_ids, evidence)
        assert result.passed is False
        assert any("Hallucinated" in e for e in result.errors)
        # Auto-fix: hallucinated citation should be stripped
        assert len(result.fixed_response.citations) == 1
        assert result.fixed_response.citations[0]["chunk_id"] == "chunk-001"

    def test_empty_answer_fails(self):
        """Empty answers should fail validation."""
        response = _make_response(answer="", citations=[])
        result = validate_response(response, set(), [])
        assert result.passed is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_no_evidence_forces_low_confidence(self):
        """When no evidence is retrieved, confidence must be low."""
        response = _make_response(
            answer="I cannot answer this from the available evidence.",
            citations=[],
            confidence="high",  # incorrectly set high
        )
        result = validate_response(response, set(), [])
        assert result.fixed_response.confidence == "low"

    def test_invalid_confidence_corrected(self):
        """Invalid confidence values should be corrected to 'low'."""
        response = _make_response(confidence="very-high")
        result = validate_response(response, {"c1"}, [{"chunk_id": "c1", "text": "X"}])
        assert result.fixed_response.confidence == "low"
        assert any("Invalid confidence" in w for w in result.warnings)

    def test_citation_missing_chunk_id_fails(self):
        """Citations without chunk_id should be flagged."""
        response = _make_response(
            answer="Some answer here that is meaningful.",
            citations=[{"document_id": "doc-1", "page": 1}],  # missing chunk_id
        )
        result = validate_response(response, set(), [])
        assert result.passed is False
        assert any("missing chunk_id" in e.lower() for e in result.errors)
