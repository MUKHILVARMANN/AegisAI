"""
AegisAI — Output Validator
Validates LLM responses before they reach the user.

Checks:
1. JSON schema conformance
2. Citation verification — every cited chunk_id must be in the retrieved evidence set
3. Answer abstention detection — forces abstention if evidence is insufficient
4. Confidence calibration

This is a non-negotiable engineering feature from the blueprint:
"No hallucinated citations."
"""
import logging
from dataclasses import dataclass

from app.services.generation.llm_client import LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str]
    warnings: list[str]
    fixed_response: LLMResponse | None = None    # Auto-corrected response if fixable


def validate_response(
    response: LLMResponse,
    evidence_chunk_ids: set[str],
    evidence_chunks: list[dict],
) -> ValidationResult:
    """
    Validate a LLM response against the retrieved evidence.

    Args:
        response: The LLMResponse to validate.
        evidence_chunk_ids: Set of chunk_id strings from the retrieval step.
        evidence_chunks: Full list of retrieved chunk dicts.

    Returns:
        ValidationResult with pass/fail and any errors found.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── 1. Required field checks ───────────────────────────────────────────
    if not response.answer or not response.answer.strip():
        errors.append("answer field is empty")

    if response.confidence not in {"high", "medium", "low"}:
        warnings.append(f"Invalid confidence value: {response.confidence!r}. Defaulting to 'low'.")
        response.confidence = "low"

    # ── 2. Citation verification ───────────────────────────────────────────
    hallucinated_citations = []
    valid_citations = []

    for citation in response.citations:
        cited_id = str(citation.get("chunk_id", "")).strip()
        if not cited_id:
            errors.append("Citation missing chunk_id")
            continue

        if cited_id not in evidence_chunk_ids:
            hallucinated_citations.append(cited_id)
            logger.warning(f"HALLUCINATED citation: chunk_id={cited_id!r} not in evidence set")
        else:
            valid_citations.append(citation)

    if hallucinated_citations:
        errors.append(
            f"Hallucinated citations detected: {hallucinated_citations}. "
            f"These chunk IDs were not in the retrieved evidence."
        )
        # Auto-fix: remove hallucinated citations
        response.citations = valid_citations

    # ── 3. Abstention check ────────────────────────────────────────────────
    if not evidence_chunks:
        if response.confidence in {"high", "medium"}:
            warnings.append("No evidence chunks retrieved but confidence is not 'low'. Correcting.")
            response.confidence = "low"
        if not any(kw in response.answer.lower() for kw in ["cannot", "don't know", "no information", "insufficient"]):
            errors.append("No evidence retrieved but answer doesn't indicate abstention.")

    # ── 4. Answer length sanity ────────────────────────────────────────────
    if len(response.answer) < 10:
        errors.append("Answer is too short to be meaningful.")

    passed = len(errors) == 0
    if not passed:
        logger.warning(f"Validation FAILED: {errors}")
    else:
        logger.debug("Validation PASSED")

    return ValidationResult(
        passed=passed,
        errors=errors,
        warnings=warnings,
        fixed_response=response,   # always return (possibly auto-corrected) response
    )
