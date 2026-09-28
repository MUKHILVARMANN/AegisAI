"""
AegisAI — Intent Router / Query Orchestrator
Classifies incoming queries and routes them to the correct handler.

Route types:
  - retrieve_knowledge  → hybrid search + reranker + LLM
  - query_structured    → SQL / pandas tool on uploaded tables
  - summarize_document  → full-document summarization workflow
  - multi_step          → controlled multi-step agentic workflow
  - unsupported         → deterministic refusal (no hallucination)

Uses keyword + heuristic classification by default.
Can be upgraded to LLM-based classification by setting USE_LLM_ROUTER=true.
"""
import logging
import re
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


ROUTE_RETRIEVE = "retrieve_knowledge"
ROUTE_SQL = "query_structured_data"
ROUTE_SUMMARIZE = "summarize_document"
ROUTE_WORKFLOW = "multi_step_workflow"
ROUTE_UNSUPPORTED = "unsupported"


# ─── Keyword Signals ──────────────────────────────────────────────────────────

_SUMMARIZE_PATTERNS = re.compile(
    r"\b(summarize|summarise|summary|overview|brief|synopsis|tldr|tl;dr)\b",
    re.IGNORECASE,
)

_SQL_PATTERNS = re.compile(
    r"\b(total|count|sum|average|avg|max|min|how many|percentage|ratio|"
    r"compare|trend|chart|graph|statistics|stats|breakdown|per year|per month)\b",
    re.IGNORECASE,
)

_MULTI_STEP_PATTERNS = re.compile(
    r"\b(and then|after that|step by step|first.+then|create.+and.+send|"
    r"generate.+report|plan.+and.+execute)\b",
    re.IGNORECASE,
)

_UNSUPPORTED_PATTERNS = re.compile(
    r"\b(book a flight|order food|send email|create calendar|"
    r"browse the web|search google|weather|stock price)\b",
    re.IGNORECASE,
)


@dataclass
class RoutingDecision:
    route: str
    confidence: float       # 0.0 - 1.0
    reason: str
    latency_ms: int = 0


def classify_intent(query: str) -> RoutingDecision:
    """
    Deterministic intent classifier using regex patterns.
    Returns a RoutingDecision with route + confidence + reason.
    """
    t0 = time.perf_counter()
    q = query.strip()

    if _UNSUPPORTED_PATTERNS.search(q):
        return RoutingDecision(
            route=ROUTE_UNSUPPORTED,
            confidence=0.95,
            reason="Query matches unsupported action patterns",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    # Multi-step must be checked BEFORE summarize/sql: queries like
    # "First summarize section 4 and then compare it" contain keywords of
    # both, but require the orchestrated workflow, not a single route.
    if _MULTI_STEP_PATTERNS.search(q):
        return RoutingDecision(
            route=ROUTE_WORKFLOW,
            confidence=0.85,
            reason="Query appears to require multiple steps",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    if _SUMMARIZE_PATTERNS.search(q):
        return RoutingDecision(
            route=ROUTE_SUMMARIZE,
            confidence=0.88,
            reason="Query contains summarization keywords",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    if _SQL_PATTERNS.search(q):
        return RoutingDecision(
            route=ROUTE_SQL,
            confidence=0.80,
            reason="Query contains structured data / aggregation keywords",
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

    # Default: knowledge retrieval
    return RoutingDecision(
        route=ROUTE_RETRIEVE,
        confidence=0.70,
        reason="Default route: retrieve from knowledge base",
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
