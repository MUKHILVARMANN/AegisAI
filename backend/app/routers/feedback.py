"""AegisAI — Feedback Router. POST /feedback"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.feedback import Feedback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    request_id: str
    rating: int         # 1 = thumbs up, -1 = thumbs down
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v not in {1, -1}:
            raise ValueError("Rating must be 1 (positive) or -1 (negative)")
        return v


@router.post("", status_code=201)
async def submit_feedback(payload: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    """Submit user feedback for a specific answer."""
    fb = Feedback(
        request_id=payload.request_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(fb)
    await db.commit()
    logger.info(f"Feedback received: request_id={payload.request_id} rating={payload.rating}")
    return {"status": "ok", "message": "Feedback recorded. Thank you!"}
