"""Generate command for code-lod."""

from pathlib import Path

import structlog
import typer

from code_lod.config import get_paths, load_config
from code_lod.models import Scope
from code_lod.pipeline import pipeline_generate
from code_lod.staleness import StalenessTracker

log = structlog.get_logger()


def generate(
    path: Path = typer.Argument(Path.cwd(), help="Path to generate descriptions for"),
    scope: Scope = typer.Option(
        None, "--scope", "-s", help="Hierarchical level to generate"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Regenerate even if fresh"),
) -> None:
    """Generate descriptions for code entities."""
    try:
        paths = get_paths(path)
    except FileNotFoundError:
        typer.error("code-lod not initialized. Run 'code-lod init' first.")
        raise typer.Exit(1)

    typer.echo(f"Generating descriptions for {path}...")

    # Load configuration
    config = load_config(paths)
    log.info("config_loaded", provider=config.provider)

    # For now, simple implementation for Python files
    python_files = list(path.rglob("*.py")) if path.is_dir() else [path]
    # Filter to actual files only
    python_files = [f for f in python_files if f.is_file()]
    log.info("files_found", count=len(python_files))

    tracker = StalenessTracker(paths.root_dir)
    from code_lod.llm.description_generator.generator import get_generator

    generator = get_generator(config.provider)

    # Use pipeline for parallel processing
    total_generated, total_skipped = pipeline_generate(
        files=python_files,
        root_dir=paths.root_dir,
        paths=paths,
        config=config,
        generator=generator,
        tracker=tracker,
        force=force,
    )

    typer.echo(f"Generated {total_generated} descriptions")
    typer.echo(f"Skipped {total_skipped} existing descriptions")
