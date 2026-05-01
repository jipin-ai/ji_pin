"""DOCX parser — extracts structured text, headings, tables from .docx files."""

import re
from pathlib import Path
from io import BytesIO

from docx import Document
from docx.oxml.ns import qn

from src.parsing.base import BaseParser
from src.parsing.models import ParsedDocument, Section, Table


def _extract_text_from_element(elem) -> str:
    """Recursively extract text from an XML element (handles nested runs)."""
    texts = []
    for node in elem.iter():
        if node.tag.endswith('}t') and node.text:
            texts.append(node.text)
    return ''.join(texts)


def _is_heading(para) -> bool:
    """Check if paragraph is a heading (built-in heading or outline level)."""
    style_name = (para.style.name if para.style else '').lower()
    if 'heading' in style_name or 'heading' in str(para.style.style_id if para.style else '').lower():
        return True
    # Check outline level
    pPr = para._element.find(qn('w:pPr'))
    if pPr is not None:
        outline = pPr.find(qn('w:outlineLvl'))
        if outline is not None:
            return True
    return False


def _heading_level(para) -> int:
    """Extract heading level from paragraph style."""
    style_name = (para.style.name if para.style else '').lower()
    for i in range(9, 0, -1):
        if f'heading {i}' in style_name or f'heading{i}' in style_name:
            return i
    # Check outline level
    pPr = para._element.find(qn('w:pPr'))
    if pPr is not None:
        outline = pPr.find(qn('w:outlineLvl'))
        if outline is not None:
            return int(outline.get(qn('w:val'), '0')) + 1
    return 1


def _is_numbered_item(text: str) -> bool:
    """Check if text looks like a numbered list item."""
    patterns = [
        r'^\s*\(\d+\)',       # (1)
        r'^\s*（\d+）',        # （1）
        r'^\s*\d+[.、．)]',    # 1. / 1、 / 1）
        r'^\s*[一二三四五六七八九十]+[、．]',  # 一、
        r'^\s*[A-Z][.、]',    # A.
        r'^\s*第[一二三四五六七八九十\d]+[条章节]',  # 第X条
        r'^\s*[（(][一二三四五六七八九十]+[）)]',   # （一）
    ]
    return any(re.match(p, text) for p in patterns)


def _extract_table(table_element) -> Table:
    """Extract a python-docx Table into our Table model."""
    rows = []
    headers = []
    for i, row in enumerate(table_element.rows):
        cells = [cell.text.strip() for cell in row.cells]
        if i == 0:
            headers = cells
        else:
            rows.append(cells)
    return Table(headers=headers, rows=rows)


class DocxParser(BaseParser):
    """Parse .docx files into structured ParsedDocument."""

    def supported_extensions(self) -> list[str]:
        return ['.docx']

    async def parse(self, file_path: str | Path) -> ParsedDocument:
        file_path = Path(file_path)
        content = file_path.read_bytes()
        doc = Document(BytesIO(content))

        title = ""
        sections: list[Section] = []
        current_section: Section | None = None
        current_items: list[str] = []
        raw_parts: list[str] = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            raw_parts.append(text)

            if _is_heading(para):
                # Flush current section
                if current_section:
                    current_section.items = current_items.copy()
                    sections.append(current_section)
                    current_items = []

                level = _heading_level(para)
                if not title and level <= 1:
                    title = text

                current_section = Section(
                    heading=text,
                    level=level,
                    content="",
                    items=[],
                    section_id=f"s{len(sections)+1}",
                )
                continue

            if current_section is None:
                # Text before first heading
                if not title:
                    title = text[:50]
                current_section = Section(
                    heading="",
                    level=0,
                    content="",
                    items=[],
                    section_id="s0",
                )

            if _is_numbered_item(text):
                current_items.append(text)
            else:
                if current_section.content:
                    current_section.content += "\n" + text
                else:
                    current_section.content = text

        # Flush last section
        if current_section:
            current_section.items = current_items.copy()
            sections.append(current_section)

        # Extract tables
        for table in doc.tables:
            tbl = _extract_table(table)
            # Attach to the last section (rough heuristic)
            if sections:
                sections[-1].tables.append(tbl)

        return ParsedDocument(
            title=title or file_path.stem,
            sections=sections,
            raw_text="\n".join(raw_parts),
            page_count=0,  # python-docx doesn't expose page count
            file_type="docx",
        )
