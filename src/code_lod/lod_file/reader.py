"""Reader for .lod files."""

from dataclasses import dataclass
from pathlib import Path

from code_lod.lod_file.comment_parser import LodComment, parse_lod_comments
from code_lod.models import Scope


@dataclass
class LodEntry:
    """An entry from a .lod file."""

    scope: Scope
    name: str
    comment: LodComment
    signature: str = ""
    start_line: int = 0
    end_line: int = 0


class LodReader:
    """Reader for .lod files."""

    def __init__(self, path: Path) -> None:
        """Initialize the reader.

        Args:
            path: Path to the .lod file.
        """
        self.path = path

    def read(self) -> list[LodEntry]:
        """Read entries from the .lod file.

        Returns:
            List of LodEntry objects.
        """
        if not self.path.exists():
            return []

        content = self.path.read_text()
        comments = parse_lod_comments(content)

        # Parse entries based on structure
        entries = self._parse_entries(content, comments)
        return entries

    def _parse_entries(
        self, content: str, comments: list[LodComment]
    ) -> list[LodEntry]:
        """Parse entries from content and comments.

        Args:
            content: The file content.
            comments: Parsed comments.

        Returns:
            List of LodEntry objects.
        """
        # For now, simple mapping - each comment becomes an entry
        # In a more sophisticated version, we'd parse the signatures too
        entries: list[LodEntry] = []

        for comment in comments:
            # Determine scope based on structure
            # This is simplified; real implementation would parse signatures
            scope = Scope.FUNCTION  # Default
            name = "<unknown>"

            # Try to extract name from signature
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if f"@lod hash:{comment.hash}" in line:
                    # Look ahead for signature
                    for j in range(i + 1, min(i + 10, len(lines))):
                        sig_line = lines[j].strip()
                        if sig_line and not sig_line.startswith("#"):
                            # Found signature
                            if sig_line.startswith("class "):
                                scope = Scope.CLASS
                                name = self._extract_class_name(sig_line)
                            elif sig_line.startswith("def ") or sig_line.startswith(
                                "async def "
                            ):
                                scope = Scope.FUNCTION
                                name = self._extract_function_name(sig_line)
                            break
                    break

            entries.append(
                LodEntry(
                    scope=scope,
                    name=name,
                    comment=comment,
                )
            )

        return entries

    def _extract_class_name(self, signature: str) -> str:
        """Extract class name from signature.

        Args:
            signature: Class signature line.

        Returns:
            Class name.
        """
        # Remove 'class ' and find name before '(' or ':'
        sig = signature.removeprefix("class ").strip()
        name = sig.split("(")[0].split(":")[0].strip()
        return name

    def _extract_function_name(self, signature: str) -> str:
        """Extract function name from signature.

        Args:
            signature: Function signature line.

        Returns:
            Function name.
        """
        # Remove 'def ' or 'async def ' and find name before '('
        sig = signature.removeprefix("async def ").removeprefix("def ").strip()
        name = sig.split("(")[0].strip()
        return name


def read_lod_file(path: Path) -> list[LodEntry]:
    """Convenience function to read a .lod file.

    Args:
        path: Path to the .lod file.

    Returns:
        List of LodEntry objects.
    """
    reader = LodReader(path)
    return reader.read()
