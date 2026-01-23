"""Read command for code-lod."""

import json
from pathlib import Path

import typer

from code_lod.config import get_paths
from code_lod.models import Scope


def read(
    path: Path = typer.Argument(Path.cwd(), help="Path to read"),
    scope: Scope = typer.Option(None, "--scope", "-s", help="Filter by scope"),
    format_type: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json, markdown"
    ),
) -> None:
    """Read and output descriptions in LLM-consumable format."""
    try:
        paths = get_paths(path)
    except FileNotFoundError:
        typer.echo("code-lod not initialized. Run 'code-lod init' first.", err=True)
        raise typer.Exit(1)

    # Collect and output descriptions
    lod_files = list(paths.lod_dir.rglob("*.lod"))

    if format_type == "text":
        for lod_file in lod_files:
            from code_lod.lod_file.reader import read_lod_file

            entries = read_lod_file(lod_file)
            for entry in entries:
                if scope is None or entry.scope == scope:
                    typer.echo(f"[{entry.scope.value}] {entry.name}")
                    typer.echo(f"  {entry.comment.description}")
                    typer.echo()
    elif format_type == "json":
        output: list[dict] = []
        for lod_file in lod_files:
            from code_lod.lod_file.reader import read_lod_file

            entries = read_lod_file(lod_file)
            for entry in entries:
                if scope is None or entry.scope == scope:
                    output.append(
                        {
                            "scope": entry.scope.value,
                            "name": entry.name,
                            "description": entry.comment.description,
                            "stale": entry.comment.stale,
                            "hash": entry.comment.hash,
                        }
                    )
        typer.echo(json.dumps(output, indent=2))
    else:
        typer.echo(f"Unknown format: {format_type}", err=True)
        raise typer.Exit(1)
