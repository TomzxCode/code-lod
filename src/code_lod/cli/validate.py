"""Validate command for code-lod."""

from pathlib import Path

import typer

from code_lod.config import get_paths
from code_lod.staleness import StalenessTracker


def validate(
    path: Path = typer.Argument(Path.cwd(), help="Path to validate"),
    fail_on_stale: bool = typer.Option(
        False, "--fail-on-stale", help="Exit with error if stale"
    ),
) -> None:
    """Validate description freshness."""
    try:
        paths = get_paths(path)
    except FileNotFoundError:
        typer.echo("code-lod not initialized. Run 'code-lod init' first.", err=True)
        raise typer.Exit(1)

    tracker = StalenessTracker(paths.root_dir)
    stale_records = tracker.hash_index.get_all_stale()

    if stale_records:
        typer.echo(f"Found {len(stale_records)} stale descriptions")
        if fail_on_stale:
            raise typer.Exit(1)
    else:
        typer.echo("All descriptions are fresh")
