"""Generate command for code-lod."""

from pathlib import Path

import structlog
import typer

from code_lod.config import (
    configure_logging,
    get_paths,
    load_config,
    should_ignore_file,
)
from code_lod.models import Scope
from code_lod.parsers.tree_sitter_parser import get_language_map_extensions
from code_lod.pipeline import pipeline_generate
from code_lod.staleness import StalenessTracker

log = None


def generate(
    path: Path = typer.Argument(Path.cwd(), help="Path to generate descriptions for"),
    scope: Scope = typer.Option(
        None, "--scope", "-s", help="Hierarchical level to generate"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Regenerate even if fresh"),
    max_parallelism: int | None = typer.Option(
        None, "--max-parallelism", "-j", help="Maximum number of parallel workers"
    ),
) -> None:
    """Generate descriptions for code entities."""
    try:
        paths = get_paths(path)
    except FileNotFoundError:
        typer.echo("code-lod not initialized. Run 'code-lod init' first.", err=True)
        raise typer.Exit(1)

    typer.echo(f"Generating descriptions for {path}...")

    # Load configuration and set up logging
    config = load_config(paths)
    configure_logging(config.log_level)
    log = structlog.get_logger()
    log.info("config_loaded", provider=config.provider)

    # Collect files for all configured languages
    files: list[Path] = []
    if path.is_dir():
        for lang in config.languages:
            for ext in get_language_map_extensions(lang):
                files.extend(path.rglob(f"*{ext}"))
    else:
        files = [path]

    # Filter to actual files only, deduplicate, and apply ignore patterns
    files = list(
        {
            f
            for f in files
            if f.is_file()
            and not should_ignore_file(f, paths.root_dir, config.ignore_patterns)
        }
    )
    log.info("files_found", count=len(files))

    tracker = StalenessTracker(paths.root_dir)
    from code_lod.config import get_model_for_scope
    from code_lod.llm.description_generator.generator import get_generator

    try:
        generator = get_generator(
            config.provider,
            model=get_model_for_scope(config, config.provider, None),
        )
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    # Use pipeline for parallel processing
    total_generated, total_skipped = pipeline_generate(
        files=files,
        root_dir=paths.root_dir,
        paths=paths,
        config=config,
        generator=generator,
        tracker=tracker,
        force=force,
        max_parallelism=max_parallelism,
    )

    typer.echo(f"Generated {total_generated} descriptions")
    typer.echo(f"Skipped {total_skipped} existing descriptions")
