"""Tests for configuration management."""

import pytest
from pydantic import ValidationError

from code_lod.config import (
    Config,
    Paths,
    configure_logging,
    get_paths,
    load_config,
    save_config,
    should_ignore_file,
)


class TestConfigValidators:
    """Tests for Config field validators."""

    def test_defaults(self) -> None:
        """Test default configuration values."""
        config = Config()
        assert config.languages == ["python"]
        assert config.provider.value == "mock"
        assert config.max_parallelism == 8
        assert config.log_level == "info"
        assert config.ignore_patterns

    def test_valid_languages_accepted(self) -> None:
        """Test valid language names pass validation."""
        config = Config(languages=["python", "go", "rust"])
        assert config.languages == ["python", "go", "rust"]

    def test_invalid_language_rejected(self) -> None:
        """Test unsupported language names are rejected."""
        with pytest.raises(ValidationError, match="Invalid language"):
            Config(languages=["cobol"])

    def test_max_parallelism_must_be_positive(self) -> None:
        """Test max_parallelism of zero is rejected."""
        with pytest.raises(ValidationError, match="max_parallelism"):
            Config(max_parallelism=0)

    def test_log_level_normalized_to_lowercase(self) -> None:
        """Test log level is normalized to lowercase."""
        config = Config(log_level="DEBUG")
        assert config.log_level == "debug"

    def test_invalid_log_level_rejected(self) -> None:
        """Test unknown log levels are rejected."""
        with pytest.raises(ValidationError, match="Invalid log_level"):
            Config(log_level="loud")


class TestLoadConfig:
    """Tests for load_config and save_config."""

    def test_load_config_returns_default_when_missing(self, tmp_project) -> None:
        """Test missing config file returns default config."""
        paths = get_paths(tmp_project)
        paths.config_file.unlink()
        config = load_config(paths)
        assert config == Config()

    def test_load_config_roundtrip(self, tmp_project) -> None:
        """Test saving and loading a config preserves values."""
        paths = get_paths(tmp_project)
        config = Config(
            languages=["python", "go"],
            max_parallelism=4,
            log_level="warning",
        )
        save_config(config, paths)
        loaded = load_config(paths)
        assert loaded == config

    def test_load_config_raises_on_invalid_json(self, tmp_project) -> None:
        """Test invalid JSON raises ValueError with a clear message."""
        paths = get_paths(tmp_project)
        paths.config_file.write_text("{not json")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_config(paths)

    def test_load_config_raises_on_invalid_language(self, tmp_project) -> None:
        """Test invalid language in file raises ValueError."""
        paths = get_paths(tmp_project)
        paths.config_file.write_text('{"languages": ["cobol"]}')
        with pytest.raises(ValueError, match="Invalid configuration"):
            load_config(paths)


class TestShouldIgnoreFile:
    """Tests for should_ignore_file."""

    def test_ignores_test_file_pattern(self, tmp_project) -> None:
        """Test files matching *_test.* are ignored."""
        path = tmp_project / "src" / "sample_test.py"
        assert should_ignore_file(path, tmp_project, Config().ignore_patterns)

    def test_ignores_tests_directory(self, tmp_project) -> None:
        """Test files under tests/ are ignored."""
        path = tmp_project / "tests" / "test_sample.py"
        path.parent.mkdir()
        assert should_ignore_file(path, tmp_project, Config().ignore_patterns)

    def test_ignores_pyc_files(self, tmp_project) -> None:
        """Test .pyc files are ignored."""
        path = tmp_project / "src" / "module.pyc"
        assert should_ignore_file(path, tmp_project, Config().ignore_patterns)

    def test_keeps_regular_source_file(self, tmp_project) -> None:
        """Test regular source files are not ignored."""
        path = tmp_project / "src" / "sample.py"
        assert not should_ignore_file(path, tmp_project, Config().ignore_patterns)

    def test_file_outside_root_is_not_ignored(self, tmp_project, tmp_path) -> None:
        """Test files outside the project root are not ignored."""
        path = tmp_path / "elsewhere" / "sample.py"
        assert not should_ignore_file(path, tmp_project, Config().ignore_patterns)


class TestConfigureLogging:
    """Tests for configure_logging."""

    @pytest.mark.parametrize("level", ["debug", "info", "warning", "error", "critical"])
    def test_valid_levels_do_not_raise(self, level: str) -> None:
        """Test all valid log levels configure structlog without error."""
        configure_logging(level)

    def test_unknown_level_falls_back_to_info(self) -> None:
        """Test unknown levels fall back to info without raising."""
        configure_logging("not-a-level")

    def test_logging_config_is_applied(self) -> None:
        """Test structlog picks up the configured wrapper class."""
        import structlog

        configure_logging("debug")
        config = structlog.get_config()
        assert config["wrapper_class"] is structlog.make_filtering_bound_logger(10)


class TestPaths:
    """Tests for Paths and project root discovery."""

    def test_paths_are_derived_from_root(self, tmp_project) -> None:
        """Test derived paths live under .code-lod."""
        paths = Paths(tmp_project)
        assert paths.code_lod_dir == tmp_project / ".code-lod"
        assert paths.lod_dir == tmp_project / ".code-lod" / ".lod"
        assert paths.config_file == tmp_project / ".code-lod" / "config.json"
        assert paths.hash_db == tmp_project / ".code-lod" / "hash-index.db"

    def test_get_paths_finds_project_root(self, tmp_project) -> None:
        """Test get_paths walks up from a subdirectory to the project root."""
        subdir = tmp_project / "src" / "nested"
        subdir.mkdir(parents=True)
        paths = get_paths(subdir)
        assert paths.root_dir == tmp_project
