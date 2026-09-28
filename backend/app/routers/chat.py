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
from app.services.orchestration import (
    classify_intent,
    ROUTE_UNSUPPORTED,
    ROUTE_RETRIEVE,
    ROUTE_SQL,
    ROUTE_SUMMARIZE,
    ROUTE_WORKFLOW,
    execute_structured_data_query,
    execute_summarization_workflow,
    execute_multi_step_workflow,
)
from app.services.ingestion.embedder import embed_query
from app.services.retrieval.hybrid_search import hybrid_search
from app.services.retrieval.reranker import rerank
from app.services.generation.llm_client import generate_answer
from app.services.generation.validator import validate_response
from app.services.tracing.tracer import PipelineTrace, save_trace
from app.config import settings
from app.services.conversation.memory import save_message, get_or_create_conversation, get_conversation_history
from app.services.citations import build_enriched_citations

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    conversation_id: str | None = None
    document_ids: list[str] | None = None   # Filter to specific docs


class CitationSchema(BaseModel):
    chunk_id: str
    document_id: str
    page: int | None = None
    heading: str | None = None
    document_name: str = ""
    snippet: str = ""
    score: float | None = None


class ChatResponse(BaseModel):
    request_id: str
    conversation_id: str | None = None
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
    conversation_id = request.conversation_id

    try:
        # ── Conversation memory ───────────────────────────────────────────
        try:
            conversation = await get_or_create_conversation(db, conversation_id, title=request.query[:100])
            conversation_id = str(conversation.id)
            await save_message(db, conversation_id, "user", request.query)
        except Exception as e:
            logger.warning(f"Conversation memory error: {e}")
            conversation_id = conversation_id or str(uuid.uuid4())

        # ── 1. Intent routing ──────────────────────────────────────────────
        routing = classify_intent(request.query)
        trace.route = routing.route
        trace.routing_confidence = routing.confidence
        trace.routing_latency_ms = routing.latency_ms

        # ── Handle unsupported routes ──────────────────────────────────────
        if routing.route == ROUTE_UNSUPPORTED:
            unsupported_answer = "I'm sorry, this type of request is outside my scope. I can help with questions based on your uploaded documents."
            trace.finalize()
            await save_trace(db, trace)
            try:
                await save_message(db, conversation_id, "assistant", unsupported_answer, trace_id=trace.request_id)
            except Exception:
                pass
            return ChatResponse(
                request_id=trace.request_id,
                conversation_id=conversation_id,
                answer=unsupported_answer,
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

        doc_uuids = [uuid.UUID(d) for d in (request.document_ids or [])]

        # ── Handle structured data / SQL tool ──────────────────────────────
        if routing.route == ROUTE_SQL:
            sql_res = await execute_structured_data_query(db, request.query, doc_uuids or None)
            trace.finalize()
            await save_trace(db, trace)
            sql_citations = await build_enriched_citations(db, sql_res.citations)
            try:
                await save_message(db, conversation_id, "assistant", sql_res.answer, trace_id=trace.request_id)
            except Exception as e:
                logger.warning(f"Failed to save assistant message: {e}")
            return ChatResponse(
                request_id=trace.request_id,
                conversation_id=conversation_id,
                answer=sql_res.answer,
                citations=[CitationSchema(**c) for c in sql_citations],
                confidence=sql_res.confidence,
                limitations=sql_res.limitations,
                route=routing.route,
                total_latency_ms=trace.total_latency_ms or 0,
                input_tokens=0,
                output_tokens=0,
                estimated_cost_usd=0.0,
                validation_passed=True,
            )

        # ── Handle document summarization workflow ─────────────────────────
        if routing.route == ROUTE_SUMMARIZE:
            summary_res = await execute_summarization_workflow(db, request.query, doc_uuids or None)
            trace.finalize()
            await save_trace(db, trace)
            summary_citations = await build_enriched_citations(db, summary_res.citations)
            try:
                await save_message(db, conversation_id, "assistant", summary_res.answer, trace_id=trace.request_id)
            except Exception as e:
                logger.warning(f"Failed to save assistant message: {e}")
            return ChatResponse(
                request_id=trace.request_id,
                conversation_id=conversation_id,
                answer=summary_res.answer,
                citations=[CitationSchema(**c) for c in summary_citations],
                confidence=summary_res.confidence,
                limitations=summary_res.limitations,
                route=routing.route,
                total_latency_ms=trace.total_latency_ms or 0,
                input_tokens=summary_res.llm_response.input_tokens if summary_res.llm_response else 0,
                output_tokens=summary_res.llm_response.output_tokens if summary_res.llm_response else 0,
                estimated_cost_usd=summary_res.llm_response.estimated_cost_usd if summary_res.llm_response else 0.0,
                validation_passed=True,
            )

        # ── Handle controlled multi-step workflow ──────────────────────────
        if routing.route == ROUTE_WORKFLOW:
            wf_res = await execute_multi_step_workflow(db, request.query, doc_uuids or None)
            trace.finalize()
            await save_trace(db, trace)
            wf_citations = await build_enriched_citations(db, wf_res.citations)
            try:
                await save_message(db, conversation_id, "assistant", wf_res.answer, trace_id=trace.request_id)
            except Exception as e:
                logger.warning(f"Failed to save assistant message: {e}")
            return ChatResponse(
                request_id=trace.request_id,
                conversation_id=conversation_id,
                answer=wf_res.answer,
                citations=[CitationSchema(**c) for c in wf_citations],
                confidence=wf_res.confidence,
                limitations=wf_res.limitations,
                route=routing.route,
                total_latency_ms=trace.total_latency_ms or 0,
                input_tokens=wf_res.llm_response.input_tokens if wf_res.llm_response else 0,
                output_tokens=wf_res.llm_response.output_tokens if wf_res.llm_response else 0,
                estimated_cost_usd=wf_res.llm_response.estimated_cost_usd if wf_res.llm_response else 0.0,
                validation_passed=True,
            )

        # ── 2. Embed query ─────────────────────────────────────────────────
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

        # ── Abstention check if zero evidence ──────────────────────────────
        if not final_chunks:
            abstention_answer = "I cannot answer this question based on the available documents. No relevant evidence was found in the indexed knowledge base."
            trace.finalize()
            await save_trace(db, trace)
            try:
                await save_message(db, conversation_id, "assistant", abstention_answer, trace_id=trace.request_id)
            except Exception:
                pass
            return ChatResponse(
                request_id=trace.request_id,
                conversation_id=conversation_id,
                answer=abstention_answer,
                citations=[],
                confidence="low",
                limitations=["Zero matching chunks found with sufficient relevance score."],
                route=routing.route,
                total_latency_ms=trace.total_latency_ms or 0,
                validation_passed=True,
            )

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

        # ── Conversation history for multi-turn context ────────────────────
        history: list[dict] = []
        try:
            # Exclude the user message we just saved for THIS request.
            history = await get_conversation_history(db, conversation_id, limit=7)
            history = history[:-1] if history else []
            history = history[-6:]  # cap context window
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")

        # ── 6. LLM generation ──────────────────────────────────────────────
        llm_response = await generate_answer(request.query, evidence, history=history)

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

        # ── Save assistant message to conversation ─────────────────────────
        try:
            await save_message(
                db, conversation_id, "assistant", final_response.answer,
                trace_id=trace.request_id,
            )
        except Exception as e:
            logger.warning(f"Failed to save assistant message: {e}")

        # ── 9. Enrich citations to full frontend schema ───────────────────
        retrieval_scores = {
            str(c.chunk_id): c.rrf_score for c in candidates
        }
        final_citations = await build_enriched_citations(
            db,
            final_response.citations,
            evidence=evidence,
            scores=retrieval_scores,
        )

        return ChatResponse(
            request_id=trace.request_id,
            conversation_id=conversation_id,
            answer=final_response.answer,
            citations=[CitationSchema(**c) for c in final_citations],
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
