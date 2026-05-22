"""PDF parser — extracts text with page-level structure via pymupdf."""

import re
from pathlib import Path

import fitz  # pymupdf

from src.parsing.base import BaseParser
from src.parsing.models import ParsedDocument, Section


def _detect_headings(text: str) -> tuple[str, int] | None:
    """Detect if a line of text is a heading. Returns (heading_text, level) or None."""
    # Match patterns like "一、", "1.", "1.1", "第X章", "（一）"
    patterns = [
        (r'^第[一二三四五六七八九十\d]+章\s', 1),
        (r'^第[一二三四五六七八九十\d]+节\s', 2),
        (r'^[一二三四五六七八九十]+[、．]\s*', 1),
        (r'^（[一二三四五六七八九十]+）\s*', 2),
        (r'^\d+\.\d+\.\d+\s', 3),
        (r'^\d+\.\d+\s', 2),
        (r'^\d+[\.、]\s', 1),
        (r'^[A-Z][\.、]\s', 1),
    ]
    for pattern, level in patterns:
        if re.match(pattern, text):
            return text, level
    # Short lines with no punctuation ending could be headings
    if len(text) <= 40 and not text.endswith(('.', '。', ';', '；', ',')):
        if not re.match(r'^[（(]', text):
            return text, 3
    return None


def _is_numbered_item(text: str) -> bool:
    """Check if text is a numbered/bulleted item."""
    patterns = [
        r'^\s*\(\d+\)',
        r'^\s*（\d+）',
        r'^\s*\d+[.、．)]',
        r'^\s*[一二三四五六七八九十]+[、．]',
        r'^\s*[A-Z][.、]',
        r'^\s*[•●○■□▪▫➢✓✔✗✘☐☑]',
        r'^\s*[（(][一二三四五六七八九十]+[）)]',
    ]
    return any(re.match(p, text) for p in patterns)


class PdfParser(BaseParser):
    """Parse .pdf files into structured ParsedDocument using pymupdf."""

    def supported_extensions(self) -> list[str]:
        return ['.pdf']

    async def parse(self, file_path: str | Path) -> ParsedDocument:
        file_path = Path(file_path)
        doc = fitz.open(str(file_path))

        title = ""
        sections: list[Section] = []
        current_section: Section | None = None
        current_items: list[str] = []
        all_lines: list[str] = []

        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            all_lines.extend(lines)

            for line in lines:
                heading = _detect_headings(line)
                if heading:
                    heading_text, level = heading
                    # Flush current section
                    if current_section:
                        current_section.items = current_items.copy()
                        sections.append(current_section)
                        current_items = []

                    if not title and level <= 1:
                        title = heading_text

                    current_section = Section(
                        heading=heading_text,
                        level=level,
                        content="",
                        items=[],
                        page_number=page_num,
                        section_id=f"s{len(sections)+1}",
                    )
                    continue

                if current_section is None:
                    if not title:
                        title = line[:50]
                    current_section = Section(
                        heading="",
                        level=0,
                        content="",
                        items=[],
                        page_number=page_num,
                        section_id="s0",
                    )

                if _is_numbered_item(line):
                    current_items.append(line)
                else:
                    if current_section.content:
                        current_section.content += "\n" + line
                    else:
                        current_section.content = line

        # Flush last
        if current_section:
            current_section.items = current_items.copy()
            sections.append(current_section)

        doc.close()

        # ── Image extraction and recognition ──────────────────────────────────
        try:
            from src.parsing.image_extractor import ImageExtractor
            from src.config import Settings
            settings = Settings()
            if settings.image_recognition_enabled:
                _, desc = await ImageExtractor.extract_and_describe(file_path, "pdf")
                if desc and sections:
                    sections[-1].content += desc
        except ImportError:
            pass  # image_extractor not available, skip

        return ParsedDocument(
            title=title or file_path.stem,
            sections=sections,
            raw_text="\n".join(all_lines),
            page_count=len(doc),
            file_type="pdf",
        )
