"""
AegisAI — LLM Client
Unified interface for OpenAI and Gemini LLMs.
Always uses structured output (JSON schema) to prevent hallucination.
"""
import json
import logging
import time
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)

# Current prompt version — change when prompts are updated
PROMPT_VERSION = "v1.0.0"

# Cost per 1K tokens (USD) — approximate
COST_MAP = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
}


@dataclass
class LLMResponse:
    answer: str
    citations: list[dict]          # [{chunk_id, document_id, page, heading}]
    confidence: str                # "high" | "medium" | "low"
    limitations: list[str]
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model: str
    prompt_version: str = PROMPT_VERSION
    estimated_cost_usd: float = 0.0


def _build_system_prompt() -> str:
    return """You are AegisAI, a trusted enterprise knowledge assistant.
Your answers MUST be grounded exclusively in the evidence chunks provided.
Do NOT invent information not present in the evidence.

Always respond with valid JSON matching this exact schema:
{
  "answer": "Your detailed answer here",
  "citations": [
    {"chunk_id": "...", "document_id": "...", "page": 1, "heading": "..."}
  ],
  "confidence": "high | medium | low",
  "limitations": ["Any caveats or gaps in the evidence"]
}

Rules:
- Every citation must reference a chunk_id from the provided evidence.
- If the evidence is insufficient, set confidence to "low" and explain in limitations.
- If you cannot answer from evidence, set answer to "I cannot answer this from the available evidence." and explain in limitations.
- Never hallucinate citations. Only cite chunks you directly used.
"""


def _build_user_prompt(query: str, evidence_chunks: list[dict]) -> str:
    evidence_text = "\n\n".join([
        f"[CHUNK {i+1}]\nChunk ID: {c['chunk_id']}\nDocument ID: {c['document_id']}\n"
        f"Page: {c.get('page_number', 'N/A')} | Heading: {c.get('heading', 'N/A')}\n"
        f"---\n{c['text']}"
        for i, c in enumerate(evidence_chunks)
    ])

    return f"""EVIDENCE:
{evidence_text}

QUESTION:
{query}

Respond with the JSON schema as instructed."""


async def generate_answer(
    query: str,
    evidence_chunks: list[dict],
) -> LLMResponse:
    """
    Generate a structured answer grounded in evidence chunks.
    Dispatches to OpenAI or Gemini based on config.
    """
    if settings.llm_provider == "openai":
        return await _generate_openai(query, evidence_chunks)
    elif settings.llm_provider == "gemini":
        return await _generate_gemini(query, evidence_chunks)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider!r}")


async def _generate_openai(query: str, evidence_chunks: list[dict]) -> LLMResponse:
    """Generate answer using OpenAI GPT."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(query, evidence_chunks)

    t0 = time.perf_counter()

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,   # Low temperature for factual, consistent answers
        max_tokens=1024,
    )

    latency_ms = int((time.perf_counter() - t0) * 1000)
    content = response.choices[0].message.content
    usage = response.usage

    parsed = json.loads(content)
    costs = COST_MAP.get(settings.openai_model, {"input": 0, "output": 0})
    estimated_cost = (
        (usage.prompt_tokens / 1000) * costs["input"] +
        (usage.completion_tokens / 1000) * costs["output"]
    )

    return LLMResponse(
        answer=parsed.get("answer", ""),
        citations=parsed.get("citations", []),
        confidence=parsed.get("confidence", "low"),
        limitations=parsed.get("limitations", []),
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        latency_ms=latency_ms,
        model=settings.openai_model,
        estimated_cost_usd=estimated_cost,
    )


async def _generate_gemini(query: str, evidence_chunks: list[dict]) -> LLMResponse:
    """Generate answer using Google Gemini."""
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(query, evidence_chunks)

    t0 = time.perf_counter()

    response = model.generate_content(
        f"{system_prompt}\n\n{user_prompt}",
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    latency_ms = int((time.perf_counter() - t0) * 1000)
    parsed = json.loads(response.text)

    input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
    output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
    costs = COST_MAP.get(settings.gemini_model, {"input": 0, "output": 0})
    estimated_cost = (
        (input_tokens / 1000) * costs["input"] +
        (output_tokens / 1000) * costs["output"]
    )

    return LLMResponse(
        answer=parsed.get("answer", ""),
        citations=parsed.get("citations", []),
        confidence=parsed.get("confidence", "low"),
        limitations=parsed.get("limitations", []),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        model=settings.gemini_model,
        estimated_cost_usd=estimated_cost,
    )
