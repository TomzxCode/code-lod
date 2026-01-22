"""Clean command for code-lod."""

import shutil

import typer

from code_lod.config import get_paths


def clean(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove all code-lod data."""
    try:
        paths = get_paths()
    except FileNotFoundError:
        typer.error("code-lod not initialized.")
        raise typer.Exit(1)

    if not force:
        typer.confirm(f"Remove {paths.code_lod_dir} and all contents?", abort=True)

    shutil.rmtree(paths.code_lod_dir)
    typer.echo("Cleaned code-lod data")
