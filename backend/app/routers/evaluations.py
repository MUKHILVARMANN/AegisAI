"""
AegisAI — Evaluations Router
POST /evaluations/run — Run the eval benchmark
GET  /evaluations/{run_id} — Get eval run results
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.feedback import EvaluationRun, EvaluationResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evaluations", tags=["evaluations"])

# Synthetic test dataset for demo
SYNTHETIC_TEST_CASES = [
    {"id": "tc-001", "question": "What is the main purpose of AegisAI?", "expected_keywords": ["knowledge", "retrieval", "enterprise"]},
    {"id": "tc-002", "question": "How does hybrid search work?", "expected_keywords": ["vector", "bm25", "fusion", "rerank"]},
    {"id": "tc-003", "question": "What document types are supported?", "expected_keywords": ["pdf", "docx", "xlsx", "csv"]},
]


async def _run_evaluation(run_id: str, db_url: str):
    """Background evaluation runner."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.routers.chat import chat
    from fastapi.testclient import TestClient

    logger.info(f"Evaluation run {run_id} started")
    # In a real implementation, this would:
    # 1. Load test cases from DB
    # 2. Run each through the full chat pipeline
    # 3. Score with retrieval recall, faithfulness, citation precision
    # 4. Update EvaluationRun with aggregate metrics


@router.post("/run", status_code=202)
async def run_evaluation(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger an evaluation benchmark run."""
    run_id = uuid.uuid4()
    run = EvaluationRun(
        id=run_id,
        name=f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        status="running",
        test_case_count=len(SYNTHETIC_TEST_CASES),
    )
    db.add(run)
    await db.commit()

    background_tasks.add_task(_run_evaluation, str(run_id), "")
    return {"run_id": str(run_id), "status": "running", "test_cases": len(SYNTHETIC_TEST_CASES)}


@router.get("/{run_id}")
async def get_evaluation(run_id: str, db: AsyncSession = Depends(get_db)):
    """Get results for an evaluation run."""
    from sqlalchemy import select
    result = await db.execute(select(EvaluationRun).where(EvaluationRun.id == uuid.UUID(run_id)))
    run = result.scalar_one_or_none()
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    results = await db.execute(
        select(EvaluationResult).where(EvaluationResult.run_id == uuid.UUID(run_id))
    )
    items = results.scalars().all()

    return {
        "run_id": str(run.id),
        "name": run.name,
        "status": run.status,
        "test_case_count": run.test_case_count,
        "metrics": run.metrics,
        "results": [
            {
                "test_case_id": r.test_case_id,
                "question": r.question,
                "metric": r.metric,
                "score": r.score,
            }
            for r in items
        ],
        "created_at": run.created_at.isoformat(),
    }
