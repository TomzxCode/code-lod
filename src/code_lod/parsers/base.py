"""Base parser interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from code_lod.models import ParsedEntity


class BaseParser(ABC):
    """Abstract base class for code parsers."""

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language name this parser handles."""

    @abstractmethod
    def parse_file(self, path: Path) -> list[ParsedEntity]:
        """Parse a file and extract code entities.

        Args:
            path: Path to the file to parse.

        Returns:
            List of parsed entities (functions, classes, module-level).
        """

    @abstractmethod
    def parse_module(self, source: str, path: Path) -> ParsedEntity:
        """Parse a module as a whole.

        Args:
            source: The source code.
            path: Path to the file.

        Returns:
            ParsedEntity representing the module.
        """
