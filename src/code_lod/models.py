"""Data models for code-lod."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Scope(str, Enum):
    """Hierarchical scope levels for code entities."""

    PROJECT = "project"
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"


class StalenessStatus(str, Enum):
    """Staleness status of a description."""

    FRESH = "fresh"
    STALE = "stale"


class DescriptionEntity(BaseModel):
    """A code entity with its description."""

    hash: str = Field(..., description="SHA-256 hash of the normalized AST")
    description: str = Field(..., description="LLM-generated description")
    stale: bool = Field(default=False, description="Whether the description is stale")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    hash_history: list[str] = Field(
        default_factory=list, description="Previous hashes for revert detection"
    )


@dataclass(frozen=True)
class CodeLocation:
    """Location of a code entity in the source."""

    path: str
    start_line: int
    end_line: int


@dataclass
class ParsedEntity:
    """A parsed code entity from tree-sitter."""

    scope: Scope
    name: str
    location: CodeLocation
    source: str
    ast_hash: str
    language: str
    parent_name: str | None = None  # For methods, nested classes, etc.
