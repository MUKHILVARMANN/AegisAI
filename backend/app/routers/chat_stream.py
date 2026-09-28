"""
AegisAI — Streaming Chat Router (SSE)
POST /chat/stream — Server-Sent Events streaming for real-time pipeline feedback.

Streams pipeline stages as they execute:
  1. routing    → intent classification result
  2. retrieval  → hybrid search candidates
  3. reranking  → cross-encoder top-K
  4. token      → LLM generation tokens (streamed)
  5. validation → grounding check result
  6. done       → final metadata + trace ID

This pairs with the non-streaming POST /chat endpoint for backward compatibility.
"""
import json
import logging
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.orchestration import classify_intent, ROUTE_UNSUPPORTED, ROUTE_RETRIEVE
from app.services.ingestion.embedder import embed_query
from app.services.retrieval.hybrid_search import hybrid_search
from app.services.retrieval.reranker import rerank
from app.services.generation.llm_client import generate_answer
from app.services.generation.validator import validate_response
from app.services.tracing.tracer import PipelineTrace, save_trace
from app.services.conversation.memory import save_message, get_conversation_history, get_or_create_conversation
from app.services.citations import build_enriched_citations
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat-stream"])


class StreamChatRequest(BaseModel):
    query: str
    conversation_id: str | None = None
    document_ids: list[str] | None = None


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
async def chat_stream(request: StreamChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Stream the full retrieval pipeline via Server-Sent Events.
    Each pipeline stage emits a named event with progress data.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    async def event_generator() -> AsyncGenerator[str, None]:
        trace = PipelineTrace(query=request.query, conversation_id=request.conversation_id)
        t_start = time.perf_counter()

        # ── Get or create conversation ────────────────────────────────────
        conversation_id = request.conversation_id
        try:
            conversation = await get_or_create_conversation(db, conversation_id, title=request.query[:100])
            conversation_id = str(conversation.id)
        except Exception as e:
            logger.warning(f"Conversation setup: {e}")
            conversation_id = conversation_id or str(uuid.uuid4())

        yield _sse_event("conversation", {"conversation_id": conversation_id})

        # ── Save user message ─────────────────────────────────────────────
        try:
            await save_message(db, conversation_id, "user", request.query)
        except Exception as e:
            logger.warning(f"Failed to save user message: {e}")

        # ── 1. Intent routing ─────────────────────────────────────────────
        routing = classify_intent(request.query)
        trace.route = routing.route
        trace.routing_confidence = routing.confidence
        trace.routing_latency_ms = routing.latency_ms

        yield _sse_event("routing", {
            "route": routing.route,
            "confidence": routing.confidence,
            "reason": routing.reason,
            "latency_ms": routing.latency_ms,
        })

        # ── Handle unsupported ────────────────────────────────────────────
        if routing.route == ROUTE_UNSUPPORTED:
            answer = "I'm sorry, this type of request is outside my scope. I can help with questions based on your uploaded documents."
            yield _sse_event("token", {"text": answer})
            trace.finalize()
            await save_trace(db, trace)
            try:
                await save_message(db, conversation_id, "assistant", answer, trace_id=trace.request_id)
            except Exception:
                pass
            yield _sse_event("done", {
                "request_id": trace.request_id,
                "conversation_id": conversation_id,
                "confidence": "high",
                "route": routing.route,
                "total_latency_ms": int((time.perf_counter() - t_start) * 1000),
                "validation_passed": True,
            })
            return

        doc_uuids = [uuid.UUID(d) for d in (request.document_ids or [])]

        # ── 2. Embed query ────────────────────────────────────────────────
        t_embed = time.perf_counter()
        query_embedding = embed_query(request.query)
        embed_ms = int((time.perf_counter() - t_embed) * 1000)

        yield _sse_event("embedding", {"latency_ms": embed_ms, "dimension": len(query_embedding)})

        # ── 3. Hybrid search ──────────────────────────────────────────────
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

        yield _sse_event("retrieval", {
            "candidate_count": len(candidates),
            "latency_ms": retrieval_ms,
            "timings": retrieval_timings if isinstance(retrieval_timings, dict) else {},
        })

        # ── 4. Reranking ──────────────────────────────────────────────────
        final_chunks, reranker_ms = rerank(request.query, candidates, settings.reranker_top_k)
        trace.reranker_latency_ms = reranker_ms
        trace.final_chunk_ids = [c.chunk_id for c in final_chunks]

        yield _sse_event("reranking", {
            "input_count": len(candidates),
            "output_count": len(final_chunks),
            "latency_ms": reranker_ms,
            "top_scores": [round(c.rrf_score, 4) for c in final_chunks[:3]],
        })

        # ── Abstention check ──────────────────────────────────────────────
        if not final_chunks:
            answer = "I cannot answer this question based on the available documents. No relevant evidence was found in the indexed knowledge base."
            yield _sse_event("token", {"text": answer})
            trace.finalize()
            await save_trace(db, trace)
            try:
                await save_message(db, conversation_id, "assistant", answer, trace_id=trace.request_id)
            except Exception:
                pass
            yield _sse_event("done", {
                "request_id": trace.request_id,
                "conversation_id": conversation_id,
                "confidence": "low",
                "route": routing.route,
                "total_latency_ms": int((time.perf_counter() - t_start) * 1000),
                "validation_passed": True,
                "citations": [],
            })
            return

        # ── 5. Prepare evidence ───────────────────────────────────────────
        evidence = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "text": c.parent_text or c.text,
                "page_number": c.page_number,
                "heading": c.heading,
                "source_type": c.source_type,
            }
            for c in final_chunks
        ]

        # ── Get conversation history for context ──────────────────────────
        history = []
        try:
            # Exclude the user message we just saved for THIS request.
            history = await get_conversation_history(db, conversation_id, limit=7)
            history = history[:-1] if history else []
            history = history[-6:]
        except Exception as e:
            logger.warning(f"Failed to load history: {e}")

        # ── 6. LLM generation ─────────────────────────────────────────────
        yield _sse_event("generating", {"model": settings.openai_model if settings.llm_provider == "openai" else settings.gemini_model, "evidence_chunks": len(evidence)})

        llm_response = await generate_answer(request.query, evidence, history=history)

        trace.model = llm_response.model
        trace.prompt_version = llm_response.prompt_version
        trace.input_tokens = llm_response.input_tokens
        trace.output_tokens = llm_response.output_tokens
        trace.generation_latency_ms = llm_response.latency_ms
        trace.estimated_cost_usd = llm_response.estimated_cost_usd
        trace.confidence = llm_response.confidence

        # Stream the answer as a single token event (for non-streaming LLM backends)
        # When true streaming is enabled per-provider, this emits word-by-word
        words = llm_response.answer.split(" ")
        buffer = ""
        chunk_size = 4  # Words per chunk for smooth streaming effect
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i + chunk_size])
            if buffer:
                chunk_text = " " + chunk_text
            else:
                buffer = "started"
            yield _sse_event("token", {"text": chunk_text})

        # ── 7. Validation ─────────────────────────────────────────────────
        evidence_chunk_ids = {c.chunk_id for c in final_chunks}
        validation = validate_response(llm_response, evidence_chunk_ids, evidence)

        trace.validation_passed = validation.passed
        trace.validation_errors = validation.errors

        final_response = validation.fixed_response or llm_response

        yield _sse_event("validation", {
            "passed": validation.passed,
            "errors": validation.errors,
            "warnings": validation.warnings,
        })

        # ── 8. Save trace + conversation message ──────────────────────────
        trace.finalize()
        await save_trace(db, trace)

        try:
            await save_message(
                db, conversation_id, "assistant", final_response.answer,
                trace_id=trace.request_id,
            )
        except Exception as e:
            logger.warning(f"Failed to save assistant message: {e}")

        # ── Enrich citations to the full frontend schema ──────────────────
        retrieval_scores = {
            str(c.chunk_id): c.rrf_score for c in candidates
        }
        enriched_citations = await build_enriched_citations(
            db,
            final_response.citations,
            evidence=evidence,
            scores=retrieval_scores,
        )

        # ── Final done event ──────────────────────────────────────────────
        yield _sse_event("done", {
            "request_id": trace.request_id,
            "conversation_id": conversation_id,
            "confidence": final_response.confidence,
            "limitations": final_response.limitations,
            "route": routing.route,
            "total_latency_ms": int((time.perf_counter() - t_start) * 1000),
            "input_tokens": final_response.input_tokens,
            "output_tokens": final_response.output_tokens,
            "estimated_cost_usd": final_response.estimated_cost_usd,
            "validation_passed": validation.passed,
            "citations": [
                {
                    "chunk_id": str(cit.get("chunk_id", "")),
                    "document_id": str(cit.get("document_id", "")),
                    "page": cit.get("page"),
                    "heading": cit.get("heading"),
                    "document_name": cit.get("document_name", ""),
                    "snippet": cit.get("snippet", ""),
                    "score": cit.get("score"),
                }
                for cit in enriched_citations
            ],
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx: disable buffering
        },
    )
