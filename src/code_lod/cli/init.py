"""Initialize command for code-lod."""

from pathlib import Path

import typer

from code_lod.config import Config, Paths
from code_lod.llm.description_generator.generator import Provider


def init(
    languages: list[str] = typer.Option(
        ["python"], "--language", "-l", help="Languages to support"
    ),
    provider: Provider = typer.Option(
        Provider.MOCK, "--provider", "-p", help="LLM provider for descriptions"
    ),
    max_parallelism: int = typer.Option(
        8, "--max-parallelism", "-j", help="Maximum number of parallel workers"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Re-initialize even if already initialized"
    ),
) -> None:
    """Initialize code-lod in the current project directory."""
    root_dir = Path.cwd()
    paths = Paths(root_dir)

    if paths.code_lod_dir.exists():
        if not force:
            typer.confirm("code-lod already initialized. Re-initialize?", abort=True)
        typer.echo("Re-initializing code-lod...")

    # Create directory structure
    paths.code_lod_dir.mkdir(parents=True, exist_ok=True)
    paths.lod_dir.mkdir(parents=True, exist_ok=True)

    # Write config
    config = Config(
        languages=languages, provider=provider, max_parallelism=max_parallelism
    )
    config_json = config.model_dump_json(indent=2)
    paths.config_file.write_text(config_json)

    typer.echo(f"Initialized code-lod in {root_dir}")
    typer.echo(f"  Config: {paths.config_file}")
    typer.echo(f"  LOD directory: {paths.lod_dir}")
