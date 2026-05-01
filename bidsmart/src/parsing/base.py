"""Abstract base class for document parsers."""

from abc import ABC, abstractmethod
from pathlib import Path

from src.parsing.models import ParsedDocument


class BaseParser(ABC):
    """All document parsers must implement parse()."""

    @abstractmethod
    async def parse(self, file_path: str | Path) -> ParsedDocument:
        """Parse a document file and return structured representation."""
        ...

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of lowercase extensions this parser handles."""
        ...
