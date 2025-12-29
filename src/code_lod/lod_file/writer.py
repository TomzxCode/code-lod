"""Writer for .lod files."""

from pathlib import Path

from code_lod.lod_file.comment_parser import LodComment, format_lod_comment
from code_lod.models import ParsedEntity, Scope


class LodWriter:
    """Writer for .lod files."""

    def __init__(self, path: Path, language: str = "python") -> None:
        """Initialize the writer.

        Args:
            path: Path to the .lod file.
            language: Programming language for comment syntax.
        """
        self.path = path
        self.language = language
        self._lines: list[str] = []
        self._module_description: str | None = None

    def write_module(self, description: str) -> None:
        """Write module-level description.

        Args:
            description: Module description.
        """
        self._module_description = description

    def write_entity(
        self, entity: ParsedEntity, description: str, stale: bool = False
    ) -> None:
        """Write an entity description.

        Args:
            entity: The parsed entity.
            description: The description to write.
            stale: Whether the description is stale.
        """

        hash_ = entity.ast_hash
        comment = LodComment(hash=hash_, description=description, stale=stale)

        # Generate signature
        signature = self._generate_signature(entity)

        # Format and add to lines
        formatted = format_lod_comment(comment, signature, self.language)
        self._lines.append(formatted)
        self._lines.append("")  # Blank line between entries

    def _generate_signature(self, entity: ParsedEntity) -> str:
        """Generate a signature for an entity.

        Args:
            entity: The parsed entity.

        Returns:
            A signature string.
        """
        # Extract a reasonable signature from the source
        lines = entity.source.split("\n")

        if entity.scope == Scope.FUNCTION:
            # Find the function definition line
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("def ") or stripped.startswith("async def "):
                    return stripped
                # Handle other languages
                if "function" in stripped or "def" in stripped:
                    return stripped
        elif entity.scope == Scope.CLASS:
            # Find the class definition line
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("class "):
                    return stripped
                if "class" in stripped:
                    return stripped

        # Fallback: return first non-empty line
        for line in lines:
            if line.strip():
                return line.strip()

        return f"# {entity.scope.value} {entity.name}"

    def save(self) -> None:
        """Save the .lod file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Add module description at the top if present
        if self._module_description:
            header = f"# @lod description:{self._module_description}\n\n"
            self._lines.insert(0, header)

        content = "\n".join(self._lines)
        self.path.write_text(content)

    def clear(self) -> None:
        """Clear all pending writes."""
        self._lines = []
        self._module_description = None


def write_lod_file(
    path: Path,
    entities: list[tuple[ParsedEntity, str]],
    language: str = "python",
    module_description: str | None = None,
) -> None:
    """Convenience function to write a .lod file.

    Args:
        path: Path to the .lod file.
        entities: List of (entity, description) tuples.
        language: Programming language.
        module_description: Optional module-level description.
    """
    writer = LodWriter(path, language)

    if module_description:
        writer.write_module(module_description)

    for entity, description in entities:
        writer.write_entity(entity, description)

    writer.save()
