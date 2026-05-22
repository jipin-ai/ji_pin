"""Document parsing models — structured representation of parsed documents."""

from dataclasses import dataclass, field


@dataclass
class TableCell:
    text: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1


@dataclass
class Table:
    """Extracted table from a document."""
    caption: str = ""
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Section:
    """A document section with heading hierarchy."""
    heading: str
    level: int                        # 1 = top-level, 2 = sub-section, etc.
    content: str                      # plain text content
    items: list[str] = field(default_factory=list)   # numbered/bulleted items
    tables: list[Table] = field(default_factory=list)
    page_number: int = 0
    section_id: str = ""              # e.g. "3.1.2"


@dataclass
class ParsedDocument:
    """Complete parsed document ready for AI review."""
    title: str
    sections: list[Section] = field(default_factory=list)
    raw_text: str = ""                # full concatenated text
    page_count: int = 0
    file_type: str = ""               # "docx" | "pdf"

    @property
    def text(self) -> str:
        if self.raw_text:
            return self.raw_text
        parts = [self.title]
        for s in self.sections:
            if s.heading:
                parts.append(s.heading)
            if s.content:
                parts.append(s.content)
            for item in s.items:
                parts.append(f"  • {item}")
        return "\n\n".join(parts)

    @property
    def char_count(self) -> int:
        return len(self.text)

    def find_numbered_items(self) -> list[dict]:
        """Extract all numbered items across sections.

        Returns list of {section_id, heading, item_text}.
        """
        results = []
        for sec in self.sections:
            for item in sec.items:
                results.append({
                    "section_id": sec.section_id,
                    "heading": sec.heading,
                    "item_text": item,
                })
        return results
