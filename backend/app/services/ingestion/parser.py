"""
AegisAI — Document Parser
Extracts text, tables, metadata from PDF / DOCX / XLSX / CSV.
Returns a list of ParsedSection objects preserving document hierarchy.
"""
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ParsedSection:
    """A logical section extracted from a document."""
    heading: str | None
    text: str
    page_start: int | None = None
    page_end: int | None = None
    source_type: str = "text"          # "text" | "table" | "heading"
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedDocument:
    sections: list[ParsedSection]
    page_count: int | None
    doc_metadata: dict = field(default_factory=dict)


# ─── PDF ─────────────────────────────────────────────────────────────────────

def parse_pdf(file_bytes: bytes) -> ParsedDocument:
    """Parse PDF using PyMuPDF. Extracts text blocks and tables per page."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF not installed. Add 'PyMuPDF' to requirements.txt")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    sections: list[ParsedSection] = []
    current_heading: str | None = None

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # text block
                for line in block.get("lines", []):
                    line_text = " ".join(span["text"] for span in line["spans"]).strip()
                    if not line_text:
                        continue

                    # Heuristic: large bold text = heading
                    spans = line.get("spans", [])
                    if spans:
                        avg_size = sum(s["size"] for s in spans) / len(spans)
                        is_bold = any("Bold" in s.get("font", "") for s in spans)
                        if avg_size > 13 or (is_bold and avg_size > 11):
                            current_heading = line_text
                            sections.append(ParsedSection(
                                heading=line_text,
                                text=line_text,
                                page_start=page_num,
                                page_end=page_num,
                                source_type="heading",
                            ))
                            continue

                    # Accumulate into a section under current heading
                    if sections and sections[-1].source_type == "text" and sections[-1].heading == current_heading:
                        sections[-1].text += " " + line_text
                        sections[-1].page_end = page_num
                    else:
                        sections.append(ParsedSection(
                            heading=current_heading,
                            text=line_text,
                            page_start=page_num,
                            page_end=page_num,
                            source_type="text",
                        ))

            elif block["type"] == 1:  # image — skip for now
                pass

        # Extract tables from page using PyMuPDF table finder
        try:
            tabs = page.find_tables()
            for tab in tabs.tables:
                df = pd.DataFrame(tab.extract())
                table_text = df.to_markdown(index=False)
                sections.append(ParsedSection(
                    heading=current_heading,
                    text=table_text,
                    page_start=page_num,
                    page_end=page_num,
                    source_type="table",
                ))
        except Exception:
            pass  # table extraction is best-effort

    doc.close()
    return ParsedDocument(sections=sections, page_count=len(doc))


# ─── DOCX ────────────────────────────────────────────────────────────────────

def parse_docx(file_bytes: bytes) -> ParsedDocument:
    """Parse DOCX using python-docx. Preserves heading hierarchy."""
    from docx import Document as DocxDocument
    from docx.oxml.ns import qn

    docx = DocxDocument(io.BytesIO(file_bytes))
    sections: list[ParsedSection] = []
    current_heading: str | None = None
    current_text_parts: list[str] = []

    def flush_text():
        nonlocal current_text_parts
        if current_text_parts:
            sections.append(ParsedSection(
                heading=current_heading,
                text=" ".join(current_text_parts),
                source_type="text",
            ))
            current_text_parts = []

    for para in docx.paragraphs:
        style_name = para.style.name if para.style else ""
        text = para.text.strip()
        if not text:
            continue

        if style_name.startswith("Heading"):
            flush_text()
            current_heading = text
            sections.append(ParsedSection(heading=text, text=text, source_type="heading"))
        else:
            current_text_parts.append(text)

    flush_text()

    # Tables
    for table in docx.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        df = pd.DataFrame(rows[1:], columns=rows[0]) if len(rows) > 1 else pd.DataFrame(rows)
        sections.append(ParsedSection(
            heading=current_heading,
            text=df.to_markdown(index=False),
            source_type="table",
        ))

    return ParsedDocument(sections=sections, page_count=None)


# ─── XLSX ────────────────────────────────────────────────────────────────────

def parse_xlsx(file_bytes: bytes) -> ParsedDocument:
    """Parse Excel: each sheet becomes a section with table markdown."""
    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    sections: list[ParsedSection] = []
    for sheet_name in xl.sheet_names:
        df = xl.parse(sheet_name)
        table_text = df.to_markdown(index=False)
        sections.append(ParsedSection(
            heading=sheet_name,
            text=table_text,
            source_type="table",
        ))
    return ParsedDocument(sections=sections, page_count=None)


# ─── CSV ─────────────────────────────────────────────────────────────────────

def parse_csv(file_bytes: bytes) -> ParsedDocument:
    """Parse CSV as a single table section."""
    df = pd.read_csv(io.BytesIO(file_bytes))
    text = df.to_markdown(index=False)
    return ParsedDocument(
        sections=[ParsedSection(heading=None, text=text, source_type="table")],
        page_count=None,
    )


# ─── Dispatcher ──────────────────────────────────────────────────────────────

def parse_document(file_bytes: bytes, doc_type: str) -> ParsedDocument:
    """Dispatch to the correct parser by document type."""
    parsers = {
        "pdf": parse_pdf,
        "docx": parse_docx,
        "xlsx": parse_xlsx,
        "csv": parse_csv,
    }
    parser_fn = parsers.get(doc_type.lower())
    if not parser_fn:
        raise ValueError(f"Unsupported document type: {doc_type!r}")

    logger.info(f"Parsing document type={doc_type!r}")
    result = parser_fn(file_bytes)
    logger.info(f"Parsed {len(result.sections)} sections, pages={result.page_count}")
    return result
