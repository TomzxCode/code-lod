"""Hash computation for code entities."""

import hashlib
import re
from pathlib import Path


def compute_ast_hash(source: str) -> str:
    """Compute a normalized hash of source code.

    This normalizes the source by:
    - Stripping comments
    - Normalizing whitespace
    - Normalizing string literals

    Args:
        source: The source code to hash.

    Returns:
        SHA-256 hash prefixed with "sha256:".
    """
    # Normalize the source code
    normalized = _normalize_source(source)

    # Compute SHA-256 hash
    hash_obj = hashlib.sha256(normalized.encode())
    return f"sha256:{hash_obj.hexdigest()}"


def _normalize_source(source: str) -> str:
    """Normalize source code for hashing.

    This strips cosmetic changes while preserving semantic structure.

    Args:
        source: The source code to normalize.

    Returns:
        Normalized source code.
    """
    # Remove single-line comments (but preserve # in strings)
    lines = source.split("\n")
    cleaned_lines = []

    for line in lines:
        # Simple comment removal - remove everything after # that's not in a string
        # This is a basic implementation; tree-sitter based normalization is more accurate
        in_string = False
        quote_char = None
        comment_start = -1

        for i, char in enumerate(line):
            if char in ('"', "'") and (i == 0 or line[i - 1] != "\\"):
                if not in_string:
                    in_string = True
                    quote_char = char
                elif char == quote_char:
                    in_string = False
                    quote_char = None

            if not in_string and char == "#":
                comment_start = i
                break

        if comment_start >= 0:
            line = line[:comment_start]

        # Remove trailing whitespace
        line = line.rstrip()

        if line or (cleaned_lines and cleaned_lines[-1] != ""):
            cleaned_lines.append(line)

    # Join and normalize whitespace
    result = "\n".join(cleaned_lines)
    # Normalize multiple spaces to single space (outside of strings ideally)
    # This is a simple approach; tree-sitter is more accurate
    result = re.sub(r" +", " ", result)

    return result


def compute_file_hash(path: Path) -> str:
    """Compute a hash of a file's contents.

    Args:
        path: Path to the file.

    Returns:
        SHA-256 hash prefixed with "sha256:".
    """
    source = path.read_text()
    return compute_ast_hash(source)
