"""Status command for code-lod."""

from pathlib import Path

import typer

from code_lod.config import get_paths


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

    # Collect all .lod files and check status
    lod_files = list(paths.lod_dir.rglob("*.lod"))

    total_entities = 0
    stale_entities = 0
    fresh_entities = 0

    for lod_file in lod_files:
        from code_lod.lod_file.reader import read_lod_file

        entries = read_lod_file(lod_file)
        for entry in entries:
            total_entities += 1
            if entry.comment.stale:
                stale_entities += 1
                if not stale_only:
                    typer.echo(f"  [STALE] {entry.scope.value}: {entry.name}")
            else:
                fresh_entities += 1

    typer.echo(
        f"\nTotal: {total_entities} | Fresh: {fresh_entities} | Stale: {stale_entities}"
    )

    if stale_entities > 0:
        raise typer.Exit(1)
