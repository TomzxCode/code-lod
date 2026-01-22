"""Configuration management for code-lod."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from code_lod.llm.description_generator.generator import Provider


class Config(BaseModel):
    """Project configuration for code-lod."""

    languages: list[str] = field(default_factory=lambda: ["python"])
    auto_update: bool = False
    fail_on_stale: bool = False
    provider: Provider = Provider.MOCK


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
    """
    if paths is None:
        paths = get_paths()

    if not paths.config_file.exists():
        return Config()

    try:
        data = json.loads(paths.config_file.read_text())
        return Config(**data)
    except Exception:
        return Config()


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
