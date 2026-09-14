# AegisAI — Enterprise Trusted Knowledge & Decision Platform

> **Production-Grade AI Knowledge & Decision Platform with Hybrid Retrieval, Cross-Encoder Reranking, Deterministic Citation Validation, Continuous Evaluation, and End-to-End Observability.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.3-black?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_+_pgvector-336791?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com)

---

## 1. Architecture Overview

AegisAI is engineered from first principles to address the failure modes of standard enterprise RAG systems: brittle chunking, hallucinated citations, lack of observability, and unmeasured retrieval recall.

```mermaid
flowchart TD
    subgraph Client ["Frontend Layer (Next.js App)"]
        UI[Next.js Obsidian UI]
        Chat[Chat & Grounding Workspace]
        IngestUI[Document Dropzone & Table]
        TraceUI[Observability & Waterfall Viewer]
        EvalUI[Continuous Eval Dashboard]
    end

    subgraph API ["Gateway Layer (FastAPI)"]
        Router[FastAPI API Gateway]
        RateLimit[SlowAPI Token Bucket Limiter]
        Auth[Request Tracing & Structured Logging]
    end

    subgraph Ingestion ["Asynchronous Ingestion Pipeline"]
        CeleryWorker[Celery Worker Cluster]
        Parser[Multimodal Parser: PDF, DOCX, XLSX, CSV]
        Chunker[Hierarchical Parent-Child Chunker]
        Embedder[Dense Embedder: BGE-large / MiniLM]
    end

    subgraph Retrieval ["Hybrid Retrieval & Reranking"]
        Orchestrator[Intent Classifier & Router]
        DenseSearch[Dense Vector Search (pgvector HNSW)]
        BM25Search[Keyword BM25 Search (pg_trgm)]
        RRF[Reciprocal Rank Fusion (RRF k=60)]
        Reranker[Cross-Encoder Reranker]
    end

    subgraph Generation ["Grounded Generation & Auditing"]
        LLM[LLM: Claude 3.5 Sonnet / GPT-4o]
        Validator[Deterministic Grounding Validator]
        Abstention[Abstention Guardrails]
    end

    subgraph Storage ["Enterprise Storage Layer"]
        PG[(PostgreSQL 16 + pgvector)]
        MinIO[(MinIO S3-Compatible Object Store)]
        RedisCache[(Redis Cache & Task Broker)]
    end

    UI --> Router
    Router --> Orchestrator
    Router --> CeleryWorker
    CeleryWorker --> Parser --> Chunker --> Embedder --> PG
    CeleryWorker --> MinIO
    
    Orchestrator --> DenseSearch --> PG
    Orchestrator --> BM25Search --> PG
    DenseSearch --> RRF
    BM25Search --> RRF
    RRF --> Reranker --> LLM
    LLM --> Validator
    Validator --> Abstention
    Validator --> PG
    Router --> RedisCache
```

---

## 2. Core Engineering Highlights

### 2.1 Hierarchical Parent-Child Chunking
Fixed-size token windows destroy document context. AegisAI preserves semantic integrity:
- **Parent Chunks:** Full logical units (headings, policy sections, spreadsheets).
- **Child Chunks:** Granular retrieval-sized passages (128–256 tokens) embedded for dense search.
- **Context Synthesis:** When a child chunk matches, the surrounding parent context is injected into the LLM context window.

### 2.2 Hybrid Retrieval with Reciprocal Rank Fusion (RRF)
Vector similarity fails on acronyms, exact IDs, and domain terminology. Keyword search misses synonyms. AegisAI fuses both:
$$RRF\_Score(d \in D) = \sum_{m \in M} \frac{w_m}{k + r_m(d)}$$
Where $k = 60$, balanced by configurable $\alpha$ weighting, then passed to a Cross-Encoder reranker.

### 2.3 Strict Deterministic Citation Validation
Before any response is streamed or returned:
1. Every inline claim is mapped to retrieved evidence IDs.
2. If an assertion lacks verbatim or semantic overlap in the reranked set, the claim is flagged.
3. If maximum candidate relevance is below threshold ($\tau = 0.75$), the system **explicitly abstains** rather than hallucinating.

### 2.4 End-to-End Observability & Trace Waterfall
Every request generates an immutable trace record tracking:
- Request ID & Intent Classifier route
- Dense vs. BM25 candidate list and fused scores
- Cross-encoder rerank delta
- Prompt version, input/output token count, and cost breakdown
- Millisecond latency waterfall per pipeline stage

### 2.5 Continuous Evaluation Engine
Evaluates retrieval and generation quality against curated enterprise test suites:
- **Faithfulness:** Claims supported by retrieved context.
- **Citation Precision:** Ratio of valid citations to total citations.
- **Recall@K & MRR:** Retrieval coverage.
- **Abstention Accuracy:** Refusal quality on unanswerable test cases.

---

## 3. Tech Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend** | Python 3.11+, FastAPI, Structlog | Async performance, strict Pydantic v2 schemas |
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript | Standalone build, server components, obsidian design system |
| **Vector DB** | PostgreSQL 16 + pgvector | ACID guarantees, transactional metadata, HNSW indexing |
| **Caching & Queue** | Redis 7 + Celery 5.4 | Reliable asynchronous background ingestion with retries |
| **Object Store** | MinIO (S3-compatible) | Unaltered raw file storage separate from chunk embeddings |
| **Embeddings & Rerank** | BGE-large-en-v1.5, MS-MARCO Cross-Encoder | High retrieval recall and precise token reranking |
| **Deployment** | Docker, Docker Compose | Reproducible multi-container orchestration |

---

## 4. API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/documents` | Ingest PDF, DOCX, XLSX, or CSV asynchronously |
| `GET` | `/documents` | List indexed documents with chunk and section counts |
| `POST` | `/documents/{id}/reprocess` | Trigger re-chunking and re-embedding pipeline |
| `POST` | `/chat` | Query knowledge base with hybrid retrieval, citations, and confidence |
| `GET` | `/traces/{request_id}` | Retrieve pipeline execution waterfall and candidate inspection |
| `POST` | `/feedback` | Submit thumbs up/down rating per request ID |
| `POST` | `/evaluations/run` | Trigger automated 150-question benchmark run |
| `GET` | `/evaluations` | List historical evaluation runs and regression metrics |
| `GET` | `/health` | Live cluster health status (Postgres, Redis, MinIO) |
| `GET` | `/metrics` | System p95 latency, chunk count, and feedback rate |

---

## 5. Quickstart & Deployment

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend development)

### Step 1: Clone and Configure
```bash
git clone https://github.com/MUKHILVARMANN/AegisAI.git
cd AegisAI
cp .env.example .env
```

### Step 2: Start Services via Docker Compose
```bash
docker compose up --build -d
```

This boots:
- PostgreSQL + pgvector on `:5432`
- Redis on `:6379`
- MinIO Object Storage on `:9000` (Console on `:9001`)
- FastAPI Backend on `:8000` (OpenAPI docs at `/docs`)
- Celery Ingestion Worker
- Next.js Web Application on `:3000`

### Step 3: Run Standalone Frontend
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to access the interactive platform.

---

## 6. System Design & Interview Defense Notes

### Q: Why Hybrid Search instead of Dense Vectors alone?
> Dense embeddings map semantic closeness in high-dimensional space, but struggle on exact alphanumeric entities (e.g. error codes like `ERR_SENTINEL_404`, policy section `SOC2 §4.1.3`, financial ticker symbols). BM25 handles sparse lexical matches. Reciprocal Rank Fusion (RRF) normalizes the rank positions without requiring calibrated score distribution normalization.

### Q: How does the system prevent stale or duplicate indexing?
> Ingestion calculates a SHA-256 checksum of raw file contents. Duplicate uploads are idempotently resolved. Reprocessing transactions use atomic delete-and-replace cascading on `document_id`.

### Q: How do you detect and handle a retrieval failure?
> When top-K candidates from cross-encoder reranking fail to cross the minimum relevance threshold ($\tau = 0.75$), the pipeline returns an explicit abstention response with a `"confidence": "low"` rating and explanatory limitations, preventing hallucinated answers.