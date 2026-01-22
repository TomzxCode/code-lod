"""CLI interface for code-lod."""

import structlog
import typer

from code_lod.cli import (
    clean,
    config,
    generate,
    hooks,
    init,
    read,
    status,
    update,
    validate,
)

# Configure structlog for console output
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

app = typer.Typer(help="code-lod: Your code at different levels of detail")
log = structlog.get_logger()

# Register commands
app.command()(init.init)
app.command()(generate.generate)
app.command()(status.status)
app.command()(validate.validate)
app.command()(update.update)
app.command()(read.read)
app.command()(hooks.install_hook)
app.command()(hooks.uninstall_hook)
app.command()(clean.clean)
app.command()(config.config)
