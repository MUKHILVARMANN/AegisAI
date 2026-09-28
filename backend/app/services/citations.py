"""
AegisAI — Citation Enrichment Service
Maps raw LLM/tool citations ({chunk_id, document_id, page, heading}) to the
full frontend Citation schema by joining document names from the DB and
attaching evidence snippets and relevance scores.

Kept as a service (not router code) so /chat, /chat/stream, and the
orchestration workflows all emit an identical citation shape.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

logger = logging.getLogger(__name__)

SNIPPET_MAX_CHARS = 300


async def build_enriched_citations(
    db: AsyncSession,
    raw_citations: list[dict],
    evidence: list[dict] | None = None,
    scores: dict[str, float] | None = None,
) -> list[dict]:
    """
    Enrich raw citations into the frontend schema:
      - document_name: joined from the documents table ("" when unknown)
      - snippet: citation's own text, else the matching evidence text (truncated)
      - score: relevance score from the retrieval scores map, when available
    Never raises: enrichment failures degrade to missing optional fields.
    """
    evidence = evidence or []
    scores = scores or {}

    # ── Document name lookup (single batched query) ──────────────────────
    doc_ids: set[str] = set()
    for cit in raw_citations:
        did = cit.get("document_id")
        if did:
            doc_ids.add(str(did))

    names: dict[str, str] = {}
    if doc_ids:
        try:
            doc_uuids = []
            for d in doc_ids:
                try:
                    doc_uuids.append(uuid.UUID(d))
                except (ValueError, AttributeError):
                    continue
            if doc_uuids:
                result = await db.execute(
                    select(Document.id, Document.name).where(Document.id.in_(doc_uuids))
                )
                names = {str(row.id): row.name for row in result.all()}
        except Exception as e:
            logger.warning(f"Citation enrichment: failed to fetch document names: {e}")

    # ── Snippet lookup from evidence chunks ──────────────────────────────
    text_by_chunk = {
        str(e.get("chunk_id", "")): (e.get("text") or "")
        for e in evidence
    }

    enriched: list[dict] = []
    for cit in raw_citations:
        cid = str(cit.get("chunk_id", "") or "")
        did = str(cit.get("document_id", "") or "")

        snippet = cit.get("text") or text_by_chunk.get(cid, "") or ""
        if len(snippet) > SNIPPET_MAX_CHARS:
            snippet = snippet[:SNIPPET_MAX_CHARS] + "..."

        score = scores.get(cid)
        enriched.append({
            "chunk_id": cid,
            "document_id": did,
            "page": cit.get("page"),
            "heading": cit.get("heading"),
            "document_name": names.get(did, ""),
            "snippet": snippet,
            "score": round(float(score), 4) if score is not None else None,
        })

    return enriched
