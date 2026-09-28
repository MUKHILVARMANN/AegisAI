"""
AegisAI — Conversation Memory Service
Manages conversation persistence, message storage, and history retrieval.

Wires the existing Conversation/Message models into the chat pipeline
to enable multi-turn context-aware conversations.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message, MessageRole

logger = logging.getLogger(__name__)


async def get_or_create_conversation(
    db: AsyncSession,
    conversation_id: str | None,
    title: str | None = None,
) -> Conversation:
    """
    Retrieve an existing conversation or create a new one.
    If conversation_id is None, creates a new conversation.
    """
    if conversation_id:
        try:
            conv_uuid = uuid.UUID(conversation_id)
            result = await db.execute(select(Conversation).where(Conversation.id == conv_uuid))
            conversation = result.scalar_one_or_none()
            if conversation:
                return conversation
        except (ValueError, Exception) as e:
            logger.warning(f"Invalid conversation_id '{conversation_id}': {e}")

    # Create new conversation
    conversation = Conversation(
        title=title or "New Conversation",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    logger.info(f"Created conversation: {conversation.id}")
    return conversation


async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    trace_id: str | None = None,
) -> Message:
    """
    Save a message to an existing conversation.
    """
    msg = Message(
        conversation_id=uuid.UUID(conversation_id),
        role=MessageRole(role),
        content=content,
        trace_id=uuid.UUID(trace_id) if trace_id else None,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_conversation_history(
    db: AsyncSession,
    conversation_id: str,
    limit: int = 10,
) -> list[dict]:
    """
    Retrieve the most recent messages from a conversation.
    Returns list of dicts with role and content for LLM context injection.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        return []

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_uuid)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    # Reverse to chronological order
    return [
        {"role": msg.role.value, "content": msg.content}
        for msg in reversed(messages)
    ]


async def list_conversations(
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    """
    List recent conversations with their last message preview.
    """
    result = await db.execute(
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        # Get last message preview
        last_msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg_result.scalar_one_or_none()

        items.append({
            "id": str(conv.id),
            "title": conv.title or "Untitled",
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else conv.created_at.isoformat(),
            "last_message_preview": (last_msg.content[:120] + "...") if last_msg and len(last_msg.content) > 120 else (last_msg.content if last_msg else ""),
            "last_role": last_msg.role.value if last_msg else None,
        })

    return items
