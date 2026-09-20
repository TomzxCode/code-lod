"""Tests for tree-sitter based parsing."""

from pathlib import Path

from code_lod.models import Scope
from code_lod.parsers.tree_sitter_parser import (
    detect_language,
    get_language_map_extensions,
    get_parser,
)


class TestGetLanguageMapExtensions:
    """Tests for get_language_map_extensions."""

    def test_python(self) -> None:
        """Test python maps to the .py extension."""
        assert get_language_map_extensions("python") == [".py"]

    def test_typescript(self) -> None:
        """Test typescript maps to both .ts and .tsx."""
        assert get_language_map_extensions("typescript") == [".ts", ".tsx"]

    def test_unknown_language(self) -> None:
        """Test unknown languages return no extensions."""
        assert get_language_map_extensions("cobol") == []


class TestDetectLanguage:
    """Tests for detect_language."""

    def test_python_file(self) -> None:
        """Test .py files are detected as python."""
        assert detect_language(Path("src/foo.py")) == "python"

    def test_unknown_extension(self) -> None:
        """Test unknown extensions return None."""
        assert detect_language(Path("src/foo.xyz")) is None


class TestTreeSitterParser:
    """Tests for TreeSitterParser on Python sources."""

    def test_parse_file_extracts_all_entities(self, sample_file: Path) -> None:
        """Test module, functions, class, and methods are each extracted once."""
        parser = get_parser("python")
        entities = parser.parse_file(sample_file)

        scopes = [entity.scope for entity in entities]
        assert scopes == [Scope.MODULE, Scope.FUNCTION, Scope.CLASS, Scope.FUNCTION]
        names = [entity.name for entity in entities]
        assert names == ["sample", "greet", "Greeter", "greet_all"]

    def test_methods_track_parent_class(self, sample_file: Path) -> None:
        """Test methods record their parent class name."""
        parser = get_parser("python")
        entities = parser.parse_file(sample_file)
        method = entities[-1]
        assert method.scope == Scope.FUNCTION
        assert method.parent_name == "Greeter"

    def test_module_entity_covers_whole_file(self, sample_file: Path) -> None:
        """Test the module entity spans the file and uses the file stem."""
        parser = get_parser("python")
        entities = parser.parse_file(sample_file)
        module = entities[0]
        assert module.scope == Scope.MODULE
        assert module.name == "sample"
        assert module.location.start_line == 1

    def test_entity_hashes_are_stable(self, sample_file: Path) -> None:
        """Test parsing the same file twice yields identical hashes."""
        parser = get_parser("python")
        first = parser.parse_file(sample_file)
        second = parser.parse_file(sample_file)
        assert [entity.ast_hash for entity in first] == [
            entity.ast_hash for entity in second
        ]
