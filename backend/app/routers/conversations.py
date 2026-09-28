"""
AegisAI — Conversations Router
GET  /conversations              — List all conversations
GET  /conversations/{id}         — Get conversation with messages
DELETE /conversations/{id}       — Delete a conversation
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import Conversation, Message
from app.services.conversation.memory import list_conversations, get_conversation_history

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: str
    last_message_preview: str
    last_role: str | None


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    trace_id: str | None
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: str
    messages: list[MessageItem]


@router.get("", response_model=list[ConversationSummary])
async def get_conversations(db: AsyncSession = Depends(get_db)):
    """List recent conversations with last message preview."""
    items = await list_conversations(db, limit=50)
    return [ConversationSummary(**item) for item in items]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single conversation with all its messages."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    conv = await db.get(Conversation, conv_uuid)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_uuid)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()

    return ConversationDetail(
        id=str(conv.id),
        title=conv.title or "Untitled",
        created_at=conv.created_at.isoformat(),
        messages=[
            MessageItem(
                id=str(m.id),
                role=m.role.value,
                content=m.content,
                trace_id=str(m.trace_id) if m.trace_id else None,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a conversation and all its messages."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    conv = await db.get(Conversation, conv_uuid)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conv)
    await db.commit()

    return {"message": f"Conversation {conversation_id} deleted."}
