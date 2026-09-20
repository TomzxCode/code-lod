"""Tests for the SQLite hash index and data models."""

from code_lod.db import HashIndex
from code_lod.models import DescriptionEntity


class TestHashIndex:
    """Tests for HashIndex database operations."""

    def test_set_and_get_roundtrip(self, tmp_path) -> None:
        """Test storing and retrieving a description."""
        db = HashIndex(tmp_path / "hash-index.db")
        db.set("sha256:abc", "A description.")
        record = db.get("sha256:abc")
        assert record is not None
        assert record.description == "A description."
        assert record.stale is False

    def test_get_missing_returns_none(self, tmp_path) -> None:
        """Test lookups for unknown hashes return None."""
        db = HashIndex(tmp_path / "hash-index.db")
        assert db.get("sha256:missing") is None

    def test_set_upserts_description(self, tmp_path) -> None:
        """Test setting an existing hash updates its description."""
        db = HashIndex(tmp_path / "hash-index.db")
        db.set("sha256:abc", "First.")
        db.set("sha256:abc", "Second.")
        record = db.get("sha256:abc")
        assert record is not None
        assert record.description == "Second."

    def test_update_preserves_created_at(self, tmp_path) -> None:
        """Test upserts keep the original created_at timestamp."""
        db = HashIndex(tmp_path / "hash-index.db")
        db.set("sha256:abc", "First.")
        first = db.get("sha256:abc")
        assert first is not None
        db.set("sha256:abc", "Second.")
        second = db.get("sha256:abc")
        assert second is not None
        assert second.created_at == first.created_at

    def test_mark_stale_and_fresh(self, tmp_path) -> None:
        """Test staleness flags transition through mark_stale/mark_fresh."""
        db = HashIndex(tmp_path / "hash-index.db")
        db.set("sha256:abc", "A description.")
        db.mark_stale("sha256:abc")
        record = db.get("sha256:abc")
        assert record is not None
        assert record.stale is True
        stale = db.get_all_stale()
        assert [r.hash for r in stale] == ["sha256:abc"]
        db.mark_fresh("sha256:abc")
        record = db.get("sha256:abc")
        assert record is not None
        assert record.stale is False
        assert db.get_all_stale() == []

    def test_delete(self, tmp_path) -> None:
        """Test deleting a record removes it from the index."""
        db = HashIndex(tmp_path / "hash-index.db")
        db.set("sha256:abc", "A description.")
        db.delete("sha256:abc")
        assert db.get("sha256:abc") is None


class TestDescriptionEntity:
    """Tests for the DescriptionEntity model."""

    def test_timestamps_are_timezone_aware(self) -> None:
        """Test default timestamps use timezone-aware UTC datetimes."""
        entity = DescriptionEntity(hash="sha256:abc", description="A description.")
        assert entity.created_at.tzinfo is not None
        assert entity.updated_at.tzinfo is not None
