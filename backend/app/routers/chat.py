"""
AegisAI — Chat Router
POST /chat — Query the knowledge base and get a grounded, cited answer.

Full pipeline:
  intent routing → hybrid search → reranking → LLM generation → validation → trace
"""
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.orchestration.router import classify_intent, ROUTE_UNSUPPORTED, ROUTE_RETRIEVE
from app.services.ingestion.embedder import embed_query
from app.services.retrieval.hybrid_search import hybrid_search
from app.services.retrieval.reranker import rerank
from app.services.generation.llm_client import generate_answer
from app.services.generation.validator import validate_response
from app.services.tracing.tracer import PipelineTrace, save_trace
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    conversation_id: str | None = None
    document_ids: list[str] | None = None   # Filter to specific docs


class CitationSchema(BaseModel):
    chunk_id: str
    document_id: str
    page: int | None
    heading: str | None


class ChatResponse(BaseModel):
    request_id: str
    answer: str
    citations: list[CitationSchema]
    confidence: str
    limitations: list[str]
    route: str
    total_latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    validation_passed: bool


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Query AegisAI knowledge base.
    Returns a grounded answer with citations, confidence, and trace ID.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    trace = PipelineTrace(query=request.query, conversation_id=request.conversation_id)

    try:
        # ── 1. Intent routing ──────────────────────────────────────────────
        routing = classify_intent(request.query)
        trace.route = routing.route
        trace.routing_confidence = routing.confidence
        trace.routing_latency_ms = routing.latency_ms

        # ── Handle unsupported routes ──────────────────────────────────────
        if routing.route == ROUTE_UNSUPPORTED:
            trace.finalize()
            await save_trace(db, trace)
            return ChatResponse(
                request_id=trace.request_id,
                answer="I'm sorry, this type of request is outside my scope. I can help with questions based on your uploaded documents.",
                citations=[],
                confidence="high",
                limitations=["Request type not supported: " + routing.reason],
                route=routing.route,
                total_latency_ms=trace.total_latency_ms or 0,
                input_tokens=None,
                output_tokens=None,
                estimated_cost_usd=None,
                validation_passed=True,
            )

        # ── 2. Embed query ─────────────────────────────────────────────────
        doc_uuids = [uuid.UUID(d) for d in (request.document_ids or [])]
        query_embedding = embed_query(request.query)

        # ── 3. Hybrid search ───────────────────────────────────────────────
        t_retrieval = time.perf_counter()
        candidates, retrieval_timings = await hybrid_search(
            db,
            query=request.query,
            query_embedding=query_embedding,
            top_n=settings.retrieval_top_n,
            document_ids=doc_uuids or None,
        )
        retrieval_ms = int((time.perf_counter() - t_retrieval) * 1000)

        trace.retrieval_latency_ms = retrieval_ms
        trace.retrieved_chunk_ids = [c.chunk_id for c in candidates]
        trace.retrieved_scores = {c.chunk_id: c.rrf_score for c in candidates}

        # ── 4. Reranking ───────────────────────────────────────────────────
        final_chunks, reranker_ms = rerank(request.query, candidates, settings.reranker_top_k)
        trace.reranker_latency_ms = reranker_ms
        trace.final_chunk_ids = [c.chunk_id for c in final_chunks]

        # ── 5. Prepare evidence for LLM ────────────────────────────────────
        evidence = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "text": c.parent_text or c.text,   # Use parent context if available
                "page_number": c.page_number,
                "heading": c.heading,
                "source_type": c.source_type,
            }
            for c in final_chunks
        ]

        # ── 6. LLM generation ──────────────────────────────────────────────
        llm_response = await generate_answer(request.query, evidence)

        trace.model = llm_response.model
        trace.prompt_version = llm_response.prompt_version
        trace.input_tokens = llm_response.input_tokens
        trace.output_tokens = llm_response.output_tokens
        trace.generation_latency_ms = llm_response.latency_ms
        trace.estimated_cost_usd = llm_response.estimated_cost_usd
        trace.confidence = llm_response.confidence

        # ── 7. Validation ──────────────────────────────────────────────────
        evidence_chunk_ids = {c.chunk_id for c in final_chunks}
        validation = validate_response(llm_response, evidence_chunk_ids, evidence)

        trace.validation_passed = validation.passed
        trace.validation_errors = validation.errors

        final_response = validation.fixed_response or llm_response

        # ── 8. Save trace ──────────────────────────────────────────────────
        trace.finalize()
        await save_trace(db, trace)

        return ChatResponse(
            request_id=trace.request_id,
            answer=final_response.answer,
            citations=[
                CitationSchema(
                    chunk_id=str(cit.get("chunk_id", "")),
                    document_id=str(cit.get("document_id", "")),
                    page=cit.get("page"),
                    heading=cit.get("heading"),
                )
                for cit in final_response.citations
            ],
            confidence=final_response.confidence,
            limitations=final_response.limitations,
            route=routing.route,
            total_latency_ms=trace.total_latency_ms or 0,
            input_tokens=final_response.input_tokens,
            output_tokens=final_response.output_tokens,
            estimated_cost_usd=final_response.estimated_cost_usd,
            validation_passed=validation.passed,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Chat pipeline failed: {exc}")
        trace.finalize()
        try:
            await save_trace(db, trace)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Internal pipeline error. Please try again.")
