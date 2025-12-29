"""Staleness tracking for code descriptions."""

from dataclasses import dataclass, field
from pathlib import Path

from code_lod.config import get_paths
from code_lod.db import HashIndex
from code_lod.models import ParsedEntity, Scope, StalenessStatus


@dataclass
class StaleEntry:
    """An entry that has stale descriptions."""

    scope: Scope
    name: str
    path: str
    current_hash: str
    stored_hash: str | None = None


@dataclass
class FreshnessStatus:
    """Status of description freshness for a codebase."""

    total_entities: int = 0
    fresh_count: int = 0
    stale_count: int = 0
    stale_entries: list[StaleEntry] = field(default_factory=list)

    @property
    def has_stale(self) -> bool:
        """Check if there are any stale entries."""
        return self.stale_count > 0


class StalenessTracker:
    """Tracks staleness of code descriptions."""

    def __init__(self, root_dir: Path | None = None) -> None:
        """Initialize the tracker.

        Args:
            root_dir: Project root directory. If None, auto-detects.
        """
        self.paths = get_paths(root_dir)
        self.hash_index = HashIndex(self.paths.hash_db)

    def check_entity(self, entity: ParsedEntity) -> StalenessStatus:
        """Check staleness of a single entity.

        Args:
            entity: The entity to check.

        Returns:
            StalenessStatus for this entity.
        """
        status = FreshnessStatus()
        status.total_entities = 1

        record = self.hash_index.get(entity.ast_hash)

        if record is None:
            # No description exists
            status.stale_count = 1
            status.stale_entries.append(
                StaleEntry(
                    scope=entity.scope,
                    name=entity.name,
                    path=entity.location.path,
                    current_hash=entity.ast_hash,
                    stored_hash=None,
                )
            )
        elif record.stale:
            # Marked as stale in database
            status.stale_count = 1
            status.stale_entries.append(
                StaleEntry(
                    scope=entity.scope,
                    name=entity.name,
                    path=entity.location.path,
                    current_hash=entity.ast_hash,
                    stored_hash=record.hash,
                )
            )
        else:
            # Fresh
            status.fresh_count = 1

        return status

    def check_entities(self, entities: list[ParsedEntity]) -> FreshnessStatus:
        """Check staleness of multiple entities.

        Args:
            entities: List of entities to check.

        Returns:
            Combined FreshnessStatus.
        """
        status = FreshnessStatus()
        status.total_entities = len(entities)

        for entity in entities:
            record = self.hash_index.get(entity.ast_hash)

            if record is None:
                # No description exists
                status.stale_count += 1
                status.stale_entries.append(
                    StaleEntry(
                        scope=entity.scope,
                        name=entity.name,
                        path=entity.location.path,
                        current_hash=entity.ast_hash,
                        stored_hash=None,
                    )
                )
            elif record.stale:
                # Marked as stale in database
                status.stale_count += 1
                status.stale_entries.append(
                    StaleEntry(
                        scope=entity.scope,
                        name=entity.name,
                        path=entity.location.path,
                        current_hash=entity.ast_hash,
                        stored_hash=record.hash,
                    )
                )
            else:
                status.fresh_count += 1

        return status

    def mark_stale(self, hash_: str) -> None:
        """Mark a hash as stale.

        Args:
            hash_: The hash to mark.
        """
        self.hash_index.mark_stale(hash_)

    def mark_fresh(self, hash_: str) -> None:
        """Mark a hash as fresh.

        Args:
            hash_: The hash to mark.
        """
        self.hash_index.mark_fresh(hash_)

    def get_description(self, hash_: str) -> str | None:
        """Get description for a hash.

        Args:
            hash_: The hash to look up.

        Returns:
            The description, or None if not found.
        """
        record = self.hash_index.get(hash_)
        return record.description if record else None

    def set_description(
        self,
        hash_: str,
        description: str,
        stale: bool = False,
        hash_history: list[str] | None = None,
    ) -> None:
        """Store a description for a hash.

        Args:
            hash_: The hash of the entity.
            description: The description text.
            stale: Whether the description is stale.
            hash_history: Previous hashes for revert detection.
        """
        self.hash_index.set(hash_, description, stale, hash_history)

    def check_revert(self, current_hash: str) -> tuple[bool, str | None]:
        """Check if current hash matches a historical hash (revert detection).

        Args:
            current_hash: The current hash of the entity.

        Returns:
            Tuple of (is_revert, description_if_revert).
        """
        # This would need to be enhanced to track hash history properly
        # For now, basic implementation
        record = self.hash_index.get(current_hash)
        if record and not record.stale:
            return True, record.description
        return False, None
