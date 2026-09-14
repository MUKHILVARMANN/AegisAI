"""
AegisAI — Hierarchical Chunker
Implements parent-child chunking strategy:
  - Parent chunk: full section text (for context retrieval)
  - Child chunks: smaller overlapping passages (for retrieval precision)

This preserves document structure rather than blindly splitting by character count.
"""
import logging
import re
import uuid
from dataclasses import dataclass, field

from app.config import settings
from app.services.ingestion.parser import ParsedSection

logger = logging.getLogger(__name__)


@dataclass
class ChunkData:
    """Intermediate chunk representation before DB insertion."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    section_id: uuid.UUID | None = None
    parent_chunk_id: uuid.UUID | None = None
    text: str = ""
    is_parent: bool = False
    page_number: int | None = None
    heading: str | None = None
    source_type: str = "text"
    chunk_index: int = 0
    extra_metadata: dict = field(default_factory=dict)


def _split_text_into_tokens(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Simple whitespace-token based splitter.
    Splits text into overlapping windows of chunk_size tokens.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap  # sliding window

    return chunks


def chunk_document(
    document_id: uuid.UUID,
    sections: list[ParsedSection],
) -> list[ChunkData]:
    """
    Converts ParsedSections into a flat list of ChunkData objects.

    Strategy:
    1. For each section, create a PARENT chunk (full section text — used to provide context).
    2. Split the section text into CHILD chunks (retrieval-sized passages).
    3. Child chunks reference their parent by parent_chunk_id.
    4. Both parent and child carry metadata: page, heading, source_type.
    """
    all_chunks: list[ChunkData] = []
    chunk_index = 0

    for section in sections:
        text = section.text.strip()
        if not text or len(text) < 20:
            continue

        section_id = uuid.uuid4()

        # ── Parent chunk ──────────────────────────────────────────────────
        parent_id = uuid.uuid4()
        parent_chunk = ChunkData(
            id=parent_id,
            document_id=document_id,
            section_id=section_id,
            parent_chunk_id=None,
            text=text,
            is_parent=True,
            page_number=section.page_start,
            heading=section.heading,
            source_type=section.source_type,
            chunk_index=chunk_index,
        )
        all_chunks.append(parent_chunk)
        chunk_index += 1

        # ── Child chunks ──────────────────────────────────────────────────
        # Tables are kept as a single child (structure must be preserved)
        if section.source_type == "table":
            child_chunk = ChunkData(
                id=uuid.uuid4(),
                document_id=document_id,
                section_id=section_id,
                parent_chunk_id=parent_id,
                text=text,
                is_parent=False,
                page_number=section.page_start,
                heading=section.heading,
                source_type="table",
                chunk_index=chunk_index,
            )
            all_chunks.append(child_chunk)
            chunk_index += 1
        else:
            child_texts = _split_text_into_tokens(
                text,
                chunk_size=settings.child_chunk_size,
                overlap=settings.child_chunk_overlap,
            )
            for i, child_text in enumerate(child_texts):
                child_chunk = ChunkData(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    section_id=section_id,
                    parent_chunk_id=parent_id,
                    text=child_text,
                    is_parent=False,
                    page_number=section.page_start,
                    heading=section.heading,
                    source_type=section.source_type,
                    chunk_index=chunk_index,
                    extra_metadata={"sub_index": i},
                )
                all_chunks.append(child_chunk)
                chunk_index += 1

    logger.info(
        f"Chunked document {document_id}: {len(sections)} sections → {len(all_chunks)} chunks "
        f"({sum(1 for c in all_chunks if c.is_parent)} parent, "
        f"{sum(1 for c in all_chunks if not c.is_parent)} child)"
    )
    return all_chunks
