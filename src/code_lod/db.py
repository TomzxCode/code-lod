"""SQLite database management for hash indexing."""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class DescriptionRecord(BaseModel):
    """A record from the descriptions table."""

    hash: str
    description: str
    stale: bool
    created_at: str
    updated_at: str
    hash_history: str  # JSON serialized


@dataclass
class HashIndex:
    """SQLite database for hash-to-description mapping."""

    db_path: Path

    def __post_init__(self) -> None:
        """Initialize the database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS descriptions (
                    hash TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    stale BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hash_history TEXT DEFAULT '[]'
                )
                """
            )
            conn.commit()

    @contextmanager
    def _connect(self) -> Any:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get(self, hash_: str) -> DescriptionRecord | None:
        """Get a description record by hash.

        Args:
            hash_: The hash to look up.

        Returns:
            The description record, or None if not found.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM descriptions WHERE hash = ?", (hash_,)
            ).fetchone()
            if row:
                return DescriptionRecord(**dict(row))
            return None

    def set(
        self,
        hash_: str,
        description: str,
        stale: bool = False,
        hash_history: list[str] | None = None,
    ) -> None:
        """Set a description record.

        Args:
            hash_: The hash of the code entity.
            description: The LLM-generated description.
            stale: Whether the description is stale.
            hash_history: Previous hashes for revert detection.
        """
        existing = self.get(hash_)
        now = datetime.utcnow().isoformat()

        if hash_history is None:
            hash_history = []

        if existing:
            # Update existing record
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE descriptions
                    SET description = ?, stale = ?, updated_at = ?, hash_history = ?
                    WHERE hash = ?
                    """,
                    (description, stale, now, str(hash_history), hash_),
                )
                conn.commit()
        else:
            # Insert new record
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO descriptions (hash, description, stale, created_at, updated_at, hash_history)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (hash_, description, stale, now, now, str(hash_history)),
                )
                conn.commit()

    def mark_stale(self, hash_: str) -> None:
        """Mark a description as stale.

        Args:
            hash_: The hash to mark as stale.
        """
        with self._connect() as conn:
            conn.execute(
                "UPDATE descriptions SET stale = TRUE, updated_at = ? WHERE hash = ?",
                (datetime.utcnow().isoformat(), hash_),
            )
            conn.commit()

    def mark_fresh(self, hash_: str) -> None:
        """Mark a description as fresh (not stale).

        Args:
            hash_: The hash to mark as fresh.
        """
        with self._connect() as conn:
            conn.execute(
                "UPDATE descriptions SET stale = FALSE, updated_at = ? WHERE hash = ?",
                (datetime.utcnow().isoformat(), hash_),
            )
            conn.commit()

    def get_all_stale(self) -> list[DescriptionRecord]:
        """Get all stale description records.

        Returns:
            List of stale description records.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM descriptions WHERE stale = TRUE"
            ).fetchall()
            return [DescriptionRecord(**dict(row)) for row in rows]

    def delete(self, hash_: str) -> None:
        """Delete a description record.

        Args:
            hash_: The hash to delete.
        """
        with self._connect() as conn:
            conn.execute("DELETE FROM descriptions WHERE hash = ?", (hash_,))
            conn.commit()
