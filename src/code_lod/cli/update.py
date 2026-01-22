"""Update command for code-lod."""

from pathlib import Path

import typer

from code_lod.config import get_paths
from code_lod.staleness import StalenessTracker


def update(
    path: Path = typer.Argument(Path.cwd(), help="Path to update"),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", "-y", help="Update without confirmation"
    ),
) -> None:
    """Update stale descriptions."""
    try:
        paths = get_paths(path)
    except FileNotFoundError:
        typer.error("code-lod not initialized. Run 'code-lod init' first.")
        raise typer.Exit(1)

    tracker = StalenessTracker(paths.root_dir)
    stale_records = tracker.hash_index.get_all_stale()

    if not stale_records:
        typer.echo("No stale descriptions to update")
        return

    typer.echo(f"Found {len(stale_records)} stale descriptions")

    if not auto_approve:
        typer.confirm("Update all stale descriptions?", abort=True)

    # TODO: Implement full update logic
    # For now, we'd need to track which files contain stale hashes
    # This is a simplified implementation
    typer.echo("Update functionality not yet fully implemented")
