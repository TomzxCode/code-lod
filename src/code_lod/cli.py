"""CLI interface for code-lod."""

from pathlib import Path

import structlog
import typer

from code_lod.config import Config, Paths, get_paths, load_config
from code_lod.llm.generator import Provider, get_generator
from code_lod.models import Scope
from code_lod.parsers.tree_sitter_parser import get_parser
from code_lod.staleness import StalenessTracker

app = typer.Typer(help="code-lod: Your code at different levels of detail")
log = structlog.get_logger()


@app.command()
def init(
    languages: list[str] = typer.Option(
        ["python"], "--language", "-l", help="Languages to support"
    ),
    provider: Provider = typer.Option(
        Provider.MOCK, "--provider", "-p", help="LLM provider for descriptions"
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
    config = Config(languages=languages, provider=provider)
    config_json = config.model_dump_json(indent=2)
    paths.config_file.write_text(config_json)

    typer.echo(f"Initialized code-lod in {root_dir}")
    typer.echo(f"  Config: {paths.config_file}")
    typer.echo(f"  LOD directory: {paths.lod_dir}")


@app.command()
def generate(
    path: Path = typer.Argument(Path.cwd(), help="Path to generate descriptions for"),
    scope: Scope = typer.Option(
        None, "--scope", "-s", help="Hierarchical level to generate"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Regenerate even if fresh"),
) -> None:
    """Generate descriptions for code entities."""
    try:
        paths = get_paths(path)
    except FileNotFoundError:
        typer.error("code-lod not initialized. Run 'code-lod init' first.")
        raise typer.Exit(1)

    typer.echo(f"Generating descriptions for {path}...")

    # Load configuration
    config = load_config(paths)

    # For now, simple implementation for Python files
    python_files = list(path.rglob("*.py")) if path.is_dir() else [path]

    tracker = StalenessTracker(paths.root_dir)
    generator = get_generator(config.provider)

    total_generated = 0
    total_skipped = 0

    for file_path in python_files:
        if not file_path.is_file():
            continue

        # Resolve to absolute path for relative_to calculation
        file_path = file_path.resolve()

        # Detect language and get parser
        from code_lod.parsers.tree_sitter_parser import detect_language

        lang = detect_language(file_path)
        if not lang:
            log.debug("skipping_file", path=str(file_path), reason="unknown language")
            continue

        parser = get_parser(lang)
        entities = parser.parse_file(file_path)

        # Generate descriptions and write to .lod files
        from code_lod.lod_file.writer import write_lod_file

        lod_path = paths.lod_dir / file_path.relative_to(paths.root_dir)
        lod_path = lod_path.with_suffix(lod_path.suffix + ".lod")

        descriptions: list[tuple[str, str]] = []
        module_description = None

        for entity in entities:
            # Check if we need to regenerate
            if not force:
                record = tracker.hash_index.get(entity.ast_hash)
                if record and not record.stale:
                    total_skipped += 1
                    if entity.scope == Scope.MODULE:
                        module_description = record.description
                    else:
                        descriptions.append((entity.name, record.description))
                    continue

            # Generate new description
            description = generator.generate(entity)
            total_generated += 1

            # Store in database
            tracker.set_description(entity.ast_hash, description, stale=False)

            if entity.scope == Scope.MODULE:
                module_description = description
            else:
                descriptions.append((entity.name, description))

        # Write .lod file
        if descriptions or module_description:
            # Filter out module entity since it's handled separately
            non_module_entities = [e for e in entities if e.scope != Scope.MODULE]
            entity_desc_pairs = [
                (e, d)
                for e, d in zip(non_module_entities, [d for _, d in descriptions])
            ]
            write_lod_file(
                lod_path,
                entity_desc_pairs,
                lang,
                module_description,
            )

    typer.echo(f"Generated {total_generated} descriptions")
    typer.echo(f"Skipped {total_skipped} existing descriptions")


@app.command()
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
        typer.error("code-lod not initialized. Run 'code-lod init' first.")
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


@app.command()
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
        typer.error("code-lod not initialized. Run 'code-lod init' first.")
        raise typer.Exit(1)

    tracker = StalenessTracker(paths.root_dir)
    stale_records = tracker.hash_index.get_all_stale()

    if stale_records:
        typer.echo(f"Found {len(stale_records)} stale descriptions")
        if fail_on_stale:
            raise typer.Exit(1)
    else:
        typer.echo("All descriptions are fresh")


@app.command()
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


@app.command()
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
        typer.error("code-lod not initialized. Run 'code-lod init' first.")
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
        import json

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
        typer.error(f"Unknown format: {format_type}")
        raise typer.Exit(1)


@app.command()
def install_hook(
    hook_type: str = typer.Option(
        "pre-commit", "--hook-type", help="Type of hook: pre-commit or pre-push"
    ),
) -> None:
    """Install the git hook."""
    try:
        paths = get_paths()
    except FileNotFoundError:
        typer.error("code-lod not initialized. Run 'code-lod init' first.")
        raise typer.Exit(1)

    hooks_dir = paths.root_dir / ".git" / "hooks"
    if not hooks_dir.exists():
        typer.error("Not a git repository")
        raise typer.Exit(1)

    hook_script = f"""#!/bin/sh
# code-lod {hook_type} hook
code-lod validate --fail-on-stale
"""

    hook_file = hooks_dir / hook_type
    hook_file.write_text(hook_script)
    hook_file.chmod(0o755)

    typer.echo(f"Installed {hook_type} hook")


@app.command()
def uninstall_hook() -> None:
    """Remove the git hook."""
    try:
        paths = get_paths()
    except FileNotFoundError:
        typer.error("code-lod not initialized.")
        raise typer.Exit(1)

    hooks_dir = paths.root_dir / ".git" / "hooks"
    hook_file = hooks_dir / "pre-commit"

    if hook_file.exists():
        hook_file.unlink()
        typer.echo("Uninstalled pre-commit hook")
    else:
        typer.echo("No hook found")


@app.command()
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

    import shutil

    shutil.rmtree(paths.code_lod_dir)
    typer.echo("Cleaned code-lod data")


@app.command()
def config_cmd(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(None, help="Configuration value (for 'set' command)"),
) -> None:
    """Get or set configuration values."""
    typer.echo("Config command not yet implemented")


if __name__ == "__main__":
    app()
