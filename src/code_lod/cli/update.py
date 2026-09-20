"""Update command for code-lod."""

from pathlib import Path

import structlog
import typer

from code_lod.config import (
    configure_logging,
    get_paths,
    load_config,
    should_ignore_file,
)
from code_lod.pipeline import pipeline_generate
from code_lod.parsers.tree_sitter_parser import (
    detect_language,
    get_language_map_extensions,
    get_parser,
)
from code_lod.staleness import StalenessTracker


def _find_stale_files(files: list[Path], tracker: StalenessTracker) -> int:
    """Count stale entities across the given files.

    Args:
        files: Source files to scan.
        tracker: Staleness tracker with the hash index.

    Returns:
        Number of entities whose hash is missing or marked stale.
    """
    stale_count = 0
    for file_path in files:
        lang = detect_language(file_path)
        if not lang:
            continue
        try:
            parser = get_parser(lang)
            entities = parser.parse_file(file_path)
        except Exception as e:
            typer.echo(f"Error scanning {file_path}: {e}", err=True)
            continue
        for entity in entities:
            record = tracker.hash_index.get(entity.ast_hash)
            if record is None or record.stale:
                stale_count += 1
    return stale_count


def update(
    path: Path = typer.Argument(Path.cwd(), help="Path to update"),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Update without confirmation"
    ),
    max_parallelism: int | None = typer.Option(
        None, "--max-parallelism", "-j", help="Maximum number of parallel workers"
    ),
) -> None:
    """Update stale descriptions."""
    try:
        paths = get_paths(path)
    except FileNotFoundError:
        typer.echo("code-lod not initialized. Run 'code-lod init' first.", err=True)
        raise typer.Exit(1)

    # Load configuration and set up logging
    config = load_config(paths)
    configure_logging(config.log_level)
    log = structlog.get_logger()
    log.info("config_loaded", provider=config.provider)

    # Collect all files for configured languages
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

    if not files:
        typer.echo("No source files found for configured languages")
        return

    log.info("files_found", count=len(files))

    # Scan to find entities whose current hash is missing or marked stale
    tracker = StalenessTracker(paths.root_dir)
    stale_count = _find_stale_files(files, tracker)

    if stale_count == 0:
        typer.echo("No stale descriptions to update")
        return

    typer.echo(f"Found {stale_count} stale descriptions")

    if not auto_approve:
        typer.confirm("Update all stale descriptions?", abort=True)

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

    # Use pipeline to regenerate stale descriptions
    # The pipeline will check staleness and only regenerate stale entities
    total_generated, total_skipped = pipeline_generate(
        files=files,
        root_dir=paths.root_dir,
        paths=paths,
        config=config,
        generator=generator,
        tracker=tracker,
        force=False,  # Don't force, let staleness check decide
        max_parallelism=max_parallelism,
    )

    typer.echo(f"Updated {total_generated} descriptions")
    typer.echo(f"Skipped {total_skipped} descriptions (already fresh)")
