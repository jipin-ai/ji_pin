"""Document parsing pipeline — factory + convenience functions."""

from pathlib import Path

from src.parsing.base import BaseParser
from src.parsing.models import ParsedDocument
from src.parsing.docx_parser import DocxParser
from src.parsing.pdf_parser import PdfParser

# Registry
PARSERS: dict[str, BaseParser] = {
    '.docx': DocxParser(),
    '.pdf': PdfParser(),
}


def get_parser(extension: str) -> BaseParser | None:
    """Get parser for a file extension (lowercase, with dot)."""
    return PARSERS.get(extension.lower())


def supported_extensions() -> list[str]:
    return list(PARSERS.keys())


async def parse_document(file_path: str | Path) -> ParsedDocument:
    """Parse any supported document and return structured representation.

    Raises ValueError if format not supported.
    Raises FileNotFoundError if file doesn't exist.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = file_path.suffix.lower()
    parser = get_parser(ext)
    if parser is None:
        raise ValueError(f"Unsupported format: {ext}. Supported: {supported_extensions()}")

    return await parser.parse(file_path)
