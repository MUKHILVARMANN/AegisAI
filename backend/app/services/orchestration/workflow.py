"""
AegisAI — Controlled Multi-Step Workflow
Handles complex multi-step user queries and full document summarizations.
Decomposes goals into deterministic sub-tasks rather than uncontrolled agent loops.
"""
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.generation.llm_client import generate_answer, LLMResponse
from app.services.retrieval.hybrid_search import hybrid_search
from app.services.retrieval.reranker import rerank
from app.services.ingestion.embedder import embed_query

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    answer: str
    citations: list[dict]
    confidence: str
    limitations: list[str]
    steps_executed: list[str]
    llm_response: LLMResponse | None = None


async def execute_summarization_workflow(
    db: AsyncSession,
    query: str,
    document_ids: list[uuid.UUID] | None = None,
) -> WorkflowResult:
    """
    Summarize document workflow:
    1. Retrieve primary parent section chunks
    2. Extract major headings and overview text
    3. Generate executive summary with section citations
    """
    doc_filter = ""
    params: dict = {}
    if document_ids:
        # asyncpg requires an explicit type cast for array parameters.
        doc_filter = "AND document_id = ANY(CAST(:doc_ids AS uuid[]))"
        params["doc_ids"] = [str(did) for did in document_ids]

    sql = text(f"""
        SELECT id::text, document_id::text, text, heading, page_number, source_type
        FROM chunks
        WHERE is_parent = true
          {doc_filter}
        ORDER BY page_number ASC NULLS LAST, chunk_index ASC
        LIMIT 6
    """)
    rows = (await db.execute(sql, params)).fetchall()

    if not rows:
        # Fallback to any chunks
        sql_fallback = text(f"""
            SELECT id::text, document_id::text, text, heading, page_number, source_type
            FROM chunks
            WHERE 1=1 {doc_filter}
            ORDER BY created_at ASC
            LIMIT 6
        """)
        rows = (await db.execute(sql_fallback, params)).fetchall()

    if not rows:
        return WorkflowResult(
            answer="Cannot summarize: no documents or chunks are available in the specified scope.",
            citations=[],
            confidence="low",
            limitations=["Document index is empty."],
            steps_executed=["fetch_parent_sections (0 found)"],
        )

    evidence = [
        {
            "chunk_id": r.id,
            "document_id": r.document_id,
            "text": r.text[:1200],
            "page_number": r.page_number,
            "heading": r.heading or "Overview",
            "source_type": r.source_type,
        }
        for r in rows
    ]

    llm_resp = await generate_answer(
        query=f"Provide a structured executive summary with key themes and findings based on: {query}",
        evidence_chunks=evidence,
    )

    return WorkflowResult(
        answer=llm_resp.answer,
        citations=llm_resp.citations,
        confidence=llm_resp.confidence,
        limitations=llm_resp.limitations,
        steps_executed=[
            f"1. Identified {len(rows)} parent document sections",
            "2. Synthesized cross-section overview",
            "3. Enforced structured citation grounding",
        ],
        llm_response=llm_resp,
    )


async def execute_multi_step_workflow(
    db: AsyncSession,
    query: str,
    document_ids: list[uuid.UUID] | None = None,
) -> WorkflowResult:
    """
    Controlled multi-step workflow:
    1. Decompose query into sub-questions
    2. Retrieve evidence for each sub-question
    3. Merge candidates and rerank
    4. Generate multi-part synthesized response
    """
    # Deterministic sub-question split by conjunctions
    sub_questions = [
        part.strip()
        for part in query.replace(" and then ", "|").replace("; ", "|").split("|")
        if part.strip()
    ]
    if len(sub_questions) < 2:
        sub_questions = [query]

    collected_evidence: list[dict] = []
    seen_chunk_ids: set[str] = set()
    steps_log = []

    for idx, sub_q in enumerate(sub_questions[:3], start=1):
        q_emb = embed_query(sub_q)
        candidates, _ = await hybrid_search(db, sub_q, q_emb, top_n=5, document_ids=document_ids)
        reranked, _ = rerank(sub_q, candidates, top_k=2)

        for c in reranked:
            if c.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(c.chunk_id)
                collected_evidence.append({
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "text": c.parent_text or c.text,
                    "page_number": c.page_number,
                    "heading": c.heading,
                    "source_type": c.source_type,
                })
        steps_log.append(f"Step {idx}: Retrieved {len(reranked)} evidence chunks for '{sub_q[:40]}...'")

    if not collected_evidence:
        return WorkflowResult(
            answer="Unable to complete multi-step request: no relevant evidence found.",
            citations=[],
            confidence="low",
            limitations=["Zero evidence matched sub-queries."],
            steps_executed=steps_log,
        )

    llm_resp = await generate_answer(
        query=f"Synthesize a step-by-step response addressing all parts of: {query}",
        evidence_chunks=collected_evidence,
    )

    return WorkflowResult(
        answer=llm_resp.answer,
        citations=llm_resp.citations,
        confidence=llm_resp.confidence,
        limitations=llm_resp.limitations,
        steps_executed=steps_log,
        llm_response=llm_resp,
    )
