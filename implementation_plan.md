# AegisAI — Production-Grade AI Knowledge & Decision Platform

## Overview

Build a full-stack, production-style AI platform where users upload enterprise documents (PDF, DOCX, XLSX, CSV), ask questions, and receive reliable, evidence-grounded answers with inline citations, traces, and evaluation metrics.

This is **Phase 1 (Strong MVP)** — a fully working, Dockerized platform hitting all non-negotiable engineering features.

---

## Architecture

```
Frontend (Next.js)
       │
  API Gateway (FastAPI)
       │         │
Query Orch.  Ingestion Service
       │         │
 Hybrid Search  Queue/Workers (Celery + Redis)
       │         │
 Reranker    OCR/Parse/Chunk/Embed
       │         │
  LLM Gen    Object Storage (MinIO)
       │         │
 Validation  PostgreSQL + pgvector
       │
 Trace/Eval Store
```

---

## Tech Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Backend API | Python + FastAPI | Async-native, production-grade |
| Database | PostgreSQL + pgvector | Vector search + relational data |
| Cache | Redis | Rate limiting, task queuing |
| Background Workers | Celery + Redis broker | Async ingestion with retries |
| Object Storage | MinIO (S3-compatible) | Local dev, cloud-portable |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Fast, free, local |
| LLM | OpenAI GPT-4o or Gemini (configurable) | Structured output support |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Cheap, effective |
| BM25 | rank_bm25 | Keyword retrieval |
| PDF Parsing | PyMuPDF (fitz) | Fast, accurate |
| DOCX | python-docx | Native DOCX support |
| XLSX/CSV | openpyxl + pandas | Table extraction |
| Frontend | Next.js 14 (App Router) | SSR + React |
| Containers | Docker + Docker Compose | Local dev setup |

---

## Proposed Changes

### Project Structure

```
AegisAI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entrypoint
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # PostgreSQL + pgvector setup
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   ├── conversation.py
│   │   │   ├── trace.py
│   │   │   └── feedback.py
│   │   ├── routers/             # API route handlers
│   │   │   ├── documents.py     # POST/GET /documents
│   │   │   ├── chat.py          # POST /chat
│   │   │   ├── traces.py        # GET /traces/{id}
│   │   │   ├── feedback.py      # POST /feedback
│   │   │   ├── evaluations.py   # POST/GET /evaluations
│   │   │   └── health.py        # GET /health, /metrics
│   │   ├── services/
│   │   │   ├── ingestion/
│   │   │   │   ├── parser.py    # PDF/DOCX/XLSX/CSV parsing
│   │   │   │   ├── chunker.py   # Hierarchical chunking
│   │   │   │   └── embedder.py  # Embedding generation
│   │   │   ├── retrieval/
│   │   │   │   ├── vector_search.py   # pgvector search
│   │   │   │   ├── bm25_search.py     # BM25 keyword search
│   │   │   │   ├── hybrid_search.py   # RRF fusion
│   │   │   │   └── reranker.py        # Cross-encoder reranker
│   │   │   ├── orchestration/
│   │   │   │   ├── router.py          # Intent classifier
│   │   │   │   └── workflow.py        # Multi-step workflows
│   │   │   ├── generation/
│   │   │   │   ├── llm_client.py      # OpenAI/Gemini client
│   │   │   │   └── validator.py       # Schema + citation validation
│   │   │   └── tracing/
│   │   │       └── tracer.py          # Request-level tracing
│   │   └── tasks/
│   │       └── ingestion_task.py      # Celery tasks
│   ├── tests/
│   │   ├── test_chunker.py
│   │   ├── test_retrieval.py
│   │   └── test_validator.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── alembic/                 # DB migrations
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx              # Chat workspace
│   │   │   ├── documents/page.tsx    # Document library
│   │   │   ├── traces/[id]/page.tsx  # Trace detail
│   │   │   ├── evaluations/page.tsx  # Eval dashboard
│   │   │   └── settings/page.tsx     # Admin settings
│   │   ├── components/
│   │   │   ├── ChatWorkspace.tsx
│   │   │   ├── CitationCard.tsx
│   │   │   ├── DocumentUpload.tsx
│   │   │   ├── TraceViewer.tsx
│   │   │   └── EvalDashboard.tsx
│   │   └── lib/
│   │       └── api.ts               # API client
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

### Backend Components

#### [NEW] `backend/app/main.py`
FastAPI application with CORS, routers, and startup events.

#### [NEW] `backend/app/models/` (SQLAlchemy)
- `documents` — id, name, type, status, checksum, created_at
- `document_sections` — hierarchical section tracking
- `chunks` — with pgvector embedding column
- `conversations` + `messages`
- `traces` — full pipeline trace per request
- `evaluations` + `feedback`

#### [NEW] `backend/services/ingestion/`
- **parser.py**: PyMuPDF for PDF, python-docx for DOCX, pandas for CSV/XLSX
- **chunker.py**: Hierarchical chunker — creates parent sections + child retrieval chunks with metadata (page, heading, doc_id)
- **embedder.py**: sentence-transformers embeddings, batch mode

#### [NEW] `backend/services/retrieval/`
- **vector_search.py**: pgvector cosine similarity
- **bm25_search.py**: rank_bm25 in-memory index per document set
- **hybrid_search.py**: Reciprocal Rank Fusion (RRF) merging both
- **reranker.py**: cross-encoder reranking of top-N candidates

#### [NEW] `backend/services/orchestration/router.py`
Intent classifier → routes to: `retrieve_knowledge()`, `query_structured_data()`, `summarize_document()`, `multi_step_workflow()`

#### [NEW] `backend/services/generation/`
- **llm_client.py**: Structured output via OpenAI function calling / Gemini
- **validator.py**: JSON schema validation + citation verification against retrieved chunks

#### [NEW] `backend/services/tracing/tracer.py`
Captures full request trace: routing decision, retrieval latency, chunk IDs + scores, reranker latency, model/prompt version, token counts, generation latency, validation result.

#### [NEW] `backend/tasks/ingestion_task.py`
Celery task: idempotent (checksum dedup), retries on failure, updates document status throughout.

---

### Frontend Components

#### [NEW] `frontend/src/app/page.tsx` — Chat Workspace
- Message thread with streaming responses
- Inline citation cards linking to source documents
- Confidence badge (high/medium/low)
- Latency + token count display
- Thumbs up/down feedback

#### [NEW] `frontend/src/app/documents/page.tsx` — Document Library
- File upload dropzone (PDF/DOCX/XLSX/CSV)
- Ingestion status timeline (uploaded → processing → indexed → failed)
- Document metadata and chunk counts

#### [NEW] `frontend/src/app/traces/[id]/page.tsx` — Trace Viewer
- Step-by-step pipeline visualization
- Retrieval scores, reranker scores
- Token usage + cost breakdown
- Prompt version used

#### [NEW] `frontend/src/app/evaluations/page.tsx` — Evaluation Dashboard
- Run evaluation button
- Metrics table: Recall@K, MRR, faithfulness, citation precision, latency

#### [NEW] `frontend/src/app/settings/page.tsx` — Admin Settings
- Retrieval parameter tuning (top-K, top-N, reranker threshold)
- Prompt version selector
- Model selector

---

### Infrastructure

#### [NEW] `docker-compose.yml`
Services: `api`, `worker`, `frontend`, `postgres`, `redis`, `minio`

#### [NEW] `.env.example`
All required environment variables documented.

---

## Data Flow

```
Upload → POST /documents
  → Celery task queued
  → File saved to MinIO
  → Parse (PyMuPDF/docx/pandas)
  → Hierarchical chunking
  → Embed chunks (sentence-transformers)
  → Store in PostgreSQL + pgvector
  → Document status = "indexed"

Query → POST /chat
  → Intent router classifies
  → Hybrid search (vector + BM25) → RRF fusion
  → Cross-encoder reranking
  → LLM generation (structured output)
  → JSON schema validation + citation verification
  → Trace stored
  → Response with answer + citations + confidence + trace_id
```

---

## Open Questions

> [!IMPORTANT]
> **LLM Provider**: Do you have an OpenAI API key available? Or would you prefer to use Google Gemini? I'll configure whichever you prefer. The system is designed to be provider-agnostic.

> [!IMPORTANT]
> **Scope for this build**: The doc covers 7 phases over 8 weeks. I'll build **Phase 1 (MVP)** fully working with all non-negotiable engineering features. Should I also include Phase 2 (hybrid search + reranking) in this first build since these are core differentiators?

> [!NOTE]
> **Evaluation dataset**: The doc recommends 100-200 curated test cases. I'll create a synthetic set of ~20 questions covering common patterns for demo purposes.

---

## Verification Plan

### Automated Tests
```bash
pytest backend/tests/ -v
```
- `test_chunker.py` — verify hierarchical chunking produces parent/child chunks
- `test_retrieval.py` — verify hybrid search returns relevant results
- `test_validator.py` — verify citation validation catches hallucinated citations

### Manual Verification
- Upload a PDF → confirm status transitions to "indexed"
- Ask a question → confirm answer has valid citations linking to actual chunks
- View trace page → confirm all pipeline stages are visible
- Docker Compose up → confirm all services start cleanly

### Docker Smoke Test
```bash
docker-compose up -d
curl http://localhost:8000/health
```
