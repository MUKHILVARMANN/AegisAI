"""Tests for the hierarchical chunker."""
import uuid
import pytest

from app.services.ingestion.parser import ParsedSection
from app.services.ingestion.chunker import chunk_document, ChunkData


def _make_section(text: str, heading: str = "Test Section", page: int = 1, source_type: str = "text") -> ParsedSection:
    return ParsedSection(heading=heading, text=text, page_start=page, page_end=page, source_type=source_type)


class TestChunkDocument:
    def test_creates_parent_and_child_chunks(self):
        """Each section should produce at least one parent + one child chunk."""
        doc_id = uuid.uuid4()
        sections = [_make_section("This is a short section with some text content here.")]
        chunks = chunk_document(doc_id, sections)

        parents = [c for c in chunks if c.is_parent]
        children = [c for c in chunks if not c.is_parent]

        assert len(parents) >= 1, "Should have at least one parent chunk"
        assert len(children) >= 1, "Should have at least one child chunk"

    def test_parent_references_no_parent(self):
        """Parent chunks must have parent_chunk_id = None."""
        doc_id = uuid.uuid4()
        sections = [_make_section("Some text " * 100)]
        chunks = chunk_document(doc_id, sections)

        for c in chunks:
            if c.is_parent:
                assert c.parent_chunk_id is None, "Parent chunks should have no parent"

    def test_child_references_parent(self):
        """Child chunks must reference a valid parent chunk ID."""
        doc_id = uuid.uuid4()
        sections = [_make_section("Word " * 200)]
        chunks = chunk_document(doc_id, sections)

        parent_ids = {c.id for c in chunks if c.is_parent}
        for c in chunks:
            if not c.is_parent:
                assert c.parent_chunk_id in parent_ids, (
                    f"Child chunk {c.id} references non-existent parent {c.parent_chunk_id}"
                )

    def test_table_chunks_kept_intact(self):
        """Table sections should not be split — preserved as single child."""
        doc_id = uuid.uuid4()
        table_text = "| Col1 | Col2 |\n|------|------|\n| A    | B    |"
        sections = [_make_section(table_text, source_type="table")]
        chunks = chunk_document(doc_id, sections)

        table_children = [c for c in chunks if not c.is_parent and c.source_type == "table"]
        assert len(table_children) == 1, "Table should be a single child chunk"
        assert table_children[0].text == table_text

    def test_metadata_propagated(self):
        """Page number and heading must be on every chunk."""
        doc_id = uuid.uuid4()
        sections = [_make_section("Some content here.", heading="Chapter 1", page=5)]
        chunks = chunk_document(doc_id, sections)

        for c in chunks:
            assert c.page_number == 5, f"Chunk {c.id} missing page number"
            assert c.heading == "Chapter 1", f"Chunk {c.id} missing heading"

    def test_empty_sections_skipped(self):
        """Empty or very short sections should not produce chunks."""
        doc_id = uuid.uuid4()
        sections = [
            _make_section(""),
            _make_section("ok"),   # too short
            _make_section("This is valid content for chunking purposes."),
        ]
        chunks = chunk_document(doc_id, sections)
        assert len(chunks) > 0
        # Short sections should be skipped
        parents = [c for c in chunks if c.is_parent]
        assert len(parents) == 1, "Only the valid section should produce a parent"

    def test_all_chunks_belong_to_document(self):
        """All chunks must have the correct document_id."""
        doc_id = uuid.uuid4()
        sections = [_make_section("Content here " * 20)]
        chunks = chunk_document(doc_id, sections)

        for c in chunks:
            assert c.document_id == doc_id, f"Chunk {c.id} has wrong document_id"
