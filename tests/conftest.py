"""Shared fixtures for code-lod tests."""

from pathlib import Path

import pytest

from code_lod.config import Config

SAMPLE_SOURCE = '''\
"""Sample module."""


def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"


class Greeter:
    """A greeter."""

    def greet_all(self, names: list[str]) -> list[str]:
        return [greet(n) for n in names]
'''


@pytest.fixture
def tmp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create an initialized project directory and chdir into it."""
    project = tmp_path / "project"
    code_lod_dir = project / ".code-lod"
    (code_lod_dir / ".lod").mkdir(parents=True)
    (code_lod_dir / "config.json").write_text(Config().model_dump_json(indent=2))
    monkeypatch.chdir(project)
    return project


@pytest.fixture
def sample_file(tmp_project: Path) -> Path:
    """Create a sample Python module inside the project."""
    src_dir = tmp_project / "src"
    src_dir.mkdir()
    sample = src_dir / "sample.py"
    sample.write_text(SAMPLE_SOURCE)
    return sample
