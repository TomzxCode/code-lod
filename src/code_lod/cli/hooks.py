"""Git hooks commands for code-lod."""

import typer

from code_lod.config import get_paths


def install_hook(
    hook_type: str = typer.Option(
        "pre-commit", "--hook-type", help="Type of hook: pre-commit or pre-push"
    ),
) -> None:
    """Install the git hook."""
    try:
        paths = get_paths()
    except FileNotFoundError:
        typer.echo("code-lod not initialized. Run 'code-lod init' first.", err=True)
        raise typer.Exit(1)

    hooks_dir = paths.root_dir / ".git" / "hooks"
    if not hooks_dir.exists():
        typer.echo("Not a git repository", err=True)
        raise typer.Exit(1)

    hook_script = f"""#!/bin/sh
# code-lod {hook_type} hook
code-lod validate --fail-on-stale
"""

    hook_file = hooks_dir / hook_type
    hook_file.write_text(hook_script)
    hook_file.chmod(0o755)

    typer.echo(f"Installed {hook_type} hook")


def uninstall_hook() -> None:
    """Remove the git hook."""
    try:
        paths = get_paths()
    except FileNotFoundError:
        typer.echo("code-lod not initialized.", err=True)
        raise typer.Exit(1)

    hooks_dir = paths.root_dir / ".git" / "hooks"
    hook_file = hooks_dir / "pre-commit"

    if hook_file.exists():
        hook_file.unlink()
        typer.echo("Uninstalled pre-commit hook")
    else:
        typer.echo("No hook found")
