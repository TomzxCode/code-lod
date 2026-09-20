"""Configuration management for code-lod."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from code_lod.models import ModelConfig
from code_lod.parsers.tree_sitter_parser import LANGUAGE_MAP

if TYPE_CHECKING:
    from code_lod.models import Scope


class Config(BaseModel):
    """Project configuration for code-lod."""

    languages: list[str] = Field(default_factory=lambda: ["python"])
    auto_update: bool = False
    fail_on_stale: bool = False
    provider: str = Field(
        default="mock",
        description=(
            "LLM provider name (any pydantic-ai provider prefix, "
            "e.g. openai, anthropic, ollama, google, groq)"
        ),
    )
    model_settings: dict[str, ModelConfig] = Field(
        default_factory=dict,
        description="Model configuration for each provider (openai, anthropic, etc.)",
    )
    max_parallelism: int = Field(
        default=8,
        description="Maximum number of parallel LLM requests to make",
    )
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            "*.test.*",
            "*_test.*",
            "*/tests/*",
            "*/test/*",
            "*/.git/*",
            "*/node_modules/*",
            "*/venv/*",
            "*/env/*",
            "*/__pycache__/*",
            "*.pyc",
        ],
        description="File patterns to ignore (glob patterns)",
    )
    log_level: str = Field(
        default="info",
        description="Logging level: debug, info, warning, error, critical",
    )

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str]) -> list[str]:
        """Validate language names are supported."""
        supported_langs = set(LANGUAGE_MAP.values())
        invalid_langs = [lang for lang in v if lang not in supported_langs]
        if invalid_langs:
            raise ValueError(
                f"Invalid language(s): {', '.join(invalid_langs)}. "
                f"Supported languages: {', '.join(sorted(supported_langs))}"
            )
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is a non-empty name."""
        v = v.strip().lower()
        if not v:
            raise ValueError("provider must be a non-empty string")
        return v

    @field_validator("max_parallelism")
    @classmethod
    def validate_max_parallelism(cls, v: int) -> int:
        """Validate max_parallelism is positive."""
        if v < 1:
            raise ValueError("max_parallelism must be at least 1")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log_level is a valid value."""
        valid_levels = {"debug", "info", "warning", "error", "critical"}
        if v.lower() not in valid_levels:
            raise ValueError(
                f"Invalid log_level: {v}. Must be one of: {', '.join(sorted(valid_levels))}"
            )
        return v.lower()


@dataclass(frozen=True)
class Paths:
    """Standard paths for code-lod in a project."""

    root_dir: Path = field(default_factory=lambda: Path.cwd())
    code_lod_dir: Path = field(init=False)
    lod_dir: Path = field(init=False)
    config_file: Path = field(init=False)
    hash_db: Path = field(init=False)

    def __post_init__(self) -> None:
        """Set derived paths."""
        object.__setattr__(self, "code_lod_dir", self.root_dir / ".code-lod")
        object.__setattr__(self, "lod_dir", self.code_lod_dir / ".lod")
        object.__setattr__(self, "config_file", self.code_lod_dir / "config.json")
        object.__setattr__(self, "hash_db", self.code_lod_dir / "hash-index.db")


def find_project_root(start_path: Path | None = None) -> Path:
    """Find the project root by looking for .code-lod directory.

    Args:
        start_path: Path to start searching from (default: current directory).

    Returns:
        The project root directory.

    Raises:
        FileNotFoundError: If no .code-lod directory is found.
    """
    if start_path is None:
        start_path = Path.cwd()

    path = start_path.resolve()
    while path != path.parent:
        if (path / ".code-lod").exists():
            return path
        path = path.parent

    raise FileNotFoundError(f"No .code-lod directory found from {start_path}")


def get_paths(root_dir: Path | None = None) -> Paths:
    """Get Paths object for the project.

    Args:
        root_dir: Starting path to search from. If None, auto-detects from cwd.

    Returns:
        Paths object with all standard paths.
    """
    # Always find the actual project root (directory containing .code-lod)
    actual_root = find_project_root(root_dir)
    return Paths(actual_root)


def load_config(paths: Paths | None = None) -> Config:
    """Load configuration from config.json.

    Args:
        paths: Paths object. If None, auto-detects.

    Returns:
        The loaded configuration, or default config if file doesn't exist.

    Raises:
        ValueError: If the config file exists but contains invalid data.
    """
    if paths is None:
        paths = get_paths()

    if not paths.config_file.exists():
        return Config()

    try:
        data = json.loads(paths.config_file.read_text())
        config = Config(**data)
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid configuration: {e}")
    except Exception as e:
        raise ValueError(f"Error loading config: {e}")


def save_config(config: Config, paths: Paths | None = None) -> None:
    """Save configuration to config.json.

    Args:
        config: The configuration to save.
        paths: Paths object. If None, auto-detects.
    """
    if paths is None:
        paths = get_paths()

    paths.config_file.parent.mkdir(parents=True, exist_ok=True)
    paths.config_file.write_text(config.model_dump_json(indent=2))


def get_model_for_scope(
    config: Config, provider: str, scope: "Scope | None"
) -> str | None:
    """Get the configured model for a specific provider and scope.

    Args:
        config: The configuration object.
        provider: The LLM provider name.
        scope: The scope to get the model for. If None, returns default.

    Returns:
        The configured model name, or None if not set.
    """

    if provider not in config.model_settings:
        return None

    model_config = config.model_settings[provider]

    if scope is None:
        return model_config.default

    return model_config.get_model_for_scope(scope)


def should_ignore_file(
    file_path: Path, root_dir: Path, ignore_patterns: list[str]
) -> bool:
    """Check if a file should be ignored based on ignore patterns.

    A pattern starting with ``*/`` also matches at the project root, so
    ``*/tests/*`` matches both ``tests/foo.py`` and ``src/tests/foo.py``.

    Args:
        file_path: Path to the file to check.
        root_dir: Root directory of the project.
        ignore_patterns: List of glob patterns to match against.

    Returns:
        True if file should be ignored, False otherwise.
    """
    import fnmatch
    import os

    try:
        rel_path = str(file_path.relative_to(root_dir))
    except ValueError:
        # File is not relative to root dir, include it
        return False

    # Use forward slashes for pattern matching
    rel_path = rel_path.replace(os.sep, "/")

    for pattern in ignore_patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Allow "*/x/*" patterns to also match "x/*" at the project root
        if pattern.startswith("*/") and fnmatch.fnmatch(rel_path, pattern[2:]):
            return True

    return False


def configure_logging(log_level: str) -> None:
    """Configure structlog with the given log level.

    Args:
        log_level: Log level string (debug, info, warning, error, critical).
    """
    import structlog

    level_map = {
        "debug": 10,
        "info": 20,
        "warning": 30,
        "error": 40,
        "critical": 50,
    }

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
        wrapper_class=structlog.make_filtering_bound_logger(
            level_map.get(log_level.lower(), 20)
        ),
    )
