"""Config command for code-lod."""

import typer


def config(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(None, help="Configuration value (for 'set' command)"),
) -> None:
    """Get or set configuration values."""
    typer.echo("Config command not yet implemented")
