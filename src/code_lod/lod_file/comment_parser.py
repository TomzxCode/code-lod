"""Parser for @lod comments in .lod files."""

import re
from dataclasses import dataclass
from enum import Enum


class CommentType(str, Enum):
    """Types of @lod comment keys."""

    HASH = "hash"
    STALE = "stale"
    DESCRIPTION = "description"


@dataclass
class LodComment:
    """A parsed @lod comment block."""

    hash: str | None = None
    stale: bool = False
    description: str = ""

    def is_complete(self) -> bool:
        """Check if the comment has all required fields."""
        return self.hash is not None and bool(self.description)


_COMMENT_REGEX = re.compile(r"^#\s*@lod\s+(\w+):\s*(.*)$")
_HASH_PREFIX_REGEX = re.compile(r"^sha256:[a-f0-9]{64}\b")


def parse_lod_comments(content: str) -> list[LodComment]:
    """Parse @lod comments from file content.

    Args:
        content: The content of a .lod file.

    Returns:
        List of parsed LodComment objects.
    """
    comments: list[LodComment] = []
    current_comment = LodComment()

    for line in content.split("\n"):
        match = _COMMENT_REGEX.match(line)
        if match:
            key = match.group(1).lower()
            value = match.group(2).strip()

            if key == CommentType.HASH:
                # Handle "hash:sha256:... stale:true" format on same line
                # Extract the hash part (before "stale:")
                parts = value.split()
                hash_value = parts[0] if parts else value

                # Validate hash format
                if _HASH_PREFIX_REGEX.match(hash_value):
                    # If we have a complete comment, save it and start new
                    if current_comment.is_complete():
                        comments.append(current_comment)
                        current_comment = LodComment()
                    current_comment.hash = hash_value

                    # Check if stale is on the same line
                    if len(parts) > 1:
                        for part in parts[1:]:
                            if part.startswith("stale:"):
                                stale_value = part.split(":", 1)[1].lower()
                                current_comment.stale = stale_value in (
                                    "true",
                                    "1",
                                    "yes",
                                )

            elif key == CommentType.STALE:
                current_comment.stale = value.lower() in ("true", "1", "yes")

            elif key == CommentType.DESCRIPTION:
                if current_comment.description:
                    current_comment.description += " " + value
                else:
                    current_comment.description = value
        elif current_comment.description and line.strip().startswith("#"):
            # Continuation of multi-line description
            continuation = line.strip().removeprefix("#").strip()
            current_comment.description += " " + continuation

    # Don't forget the last comment
    if current_comment.is_complete():
        comments.append(current_comment)

    return comments


def format_lod_comment(
    comment: LodComment, signature: str = "", language: str = "python"
) -> str:
    """Format a LodComment as a comment block.

    Args:
        comment: The comment to format.
        signature: Optional function/class signature to include.
        language: The programming language (for comment syntax).

    Returns:
        Formatted comment block as a string.
    """
    lines = []

    # Comment prefix based on language
    comment_prefix = "#"  # Default for Python-like languages

    # Format hash and stale flags
    if comment.hash:
        stale_flag = "stale:true" if comment.stale else "stale:false"
        lines.append(f"{comment_prefix} @lod hash:{comment.hash} {stale_flag}")

    # Format description (may span multiple lines)
    if comment.description:
        desc_lines = comment.description.split("\n")
        lines.append(f"{comment_prefix} @lod description:{desc_lines[0]}")
        for line in desc_lines[1:]:
            lines.append(f"{comment_prefix} {line}")

    # Add signature if provided
    if signature:
        lines.append(signature)

    return "\n".join(lines)
