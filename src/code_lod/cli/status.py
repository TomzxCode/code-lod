"""Status command for code-lod."""

from pathlib import Path

import typer

from code_lod.config import get_paths, load_config, should_ignore_file
from code_lod.parsers.tree_sitter_parser import get_language_map_extensions, get_parser
from code_lod.staleness import StalenessTracker


def status(
    path: Path = typer.Argument(Path.cwd(), help="Path to check"),
    stale_only: bool = typer.Option(
        False, "--stale-only", help="Only show stale descriptions"
    ),
) -> None:
    """Show status of descriptions."""
    try:
        paths = get_paths(path)
    except FileNotFoundError:
        typer.echo("code-lod not initialized. Run 'code-lod init' first.", err=True)
        raise typer.Exit(1)

    config = load_config(paths)
    tracker = StalenessTracker(paths.root_dir)

    # Collect all source files
    files: list[Path] = []
    if path.is_dir():
        for lang in config.languages:
            for ext in get_language_map_extensions(lang):
                files.extend(path.rglob(f"*{ext}"))
    else:
        files = [path]

    # Filter and deduplicate
    files = list(
        {
            f
            for f in files
            if f.is_file()
            and not should_ignore_file(f, paths.root_dir, config.ignore_patterns)
        }
    )

    total_entities = 0
    fresh_entities = 0
    stale_entities = 0

    for file_path in files:
        # Detect language and parse
        from code_lod.parsers.tree_sitter_parser import detect_language

        lang = detect_language(file_path)
        if not lang:
            continue

        parser = get_parser(lang)
        entities = parser.parse_file(file_path)

        for entity in entities:
            total_entities += 1

            # Check if this entity has a fresh description
            record = tracker.hash_index.get(entity.ast_hash)

            is_stale = record is None or record.stale

            if is_stale:
                stale_entities += 1
                typer.echo(
                    f"  [STALE] {entity.scope.value}: {entity.name} ({file_path.relative_to(paths.root_dir)})"
                )
            else:
                fresh_entities += 1
                if not stale_only:
                    typer.echo(
                        f"  [FRESH] {entity.scope.value}: {entity.name} ({file_path.relative_to(paths.root_dir)})"
                    )

    typer.echo(
        f"\nTotal: {total_entities} | Fresh: {fresh_entities} | Stale: {stale_entities}"
    )

    if stale_entities > 0:
        raise typer.Exit(1)
