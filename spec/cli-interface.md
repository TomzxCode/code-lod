# CLI Interface

## Overview

The CLI interface provides command-line access to all code-lod operations using Typer. Each command is implemented in a separate module for maintainability.

## Requirements

### MUST

- The system MUST provide commands: init, generate, status, validate, read, update, clean, config, hooks
- Each command MUST be implemented in a separate file under `cli/`
- The system MUST use Typer for command parsing and help text
- The system MUST auto-detect the project root from the current directory
- The system MUST provide clear error messages for common failure cases

### Command Descriptions

**init**: Initialize code-lod in a project directory
- Creates `.code-lod` directory structure
- Creates default `config.json`

**generate**: Generate descriptions for code entities
- Parses source files
- Generates descriptions via LLM
- Stores in database and `.lod` files

**status**: Check freshness status of descriptions
- Shows total, fresh, and stale counts
- Lists stale entries

**validate**: Validate descriptions
- Checks for stale descriptions
- Can fail with exit code 1 if stale entries found

**read**: Output descriptions in LLM-consumable format
- Retrieves descriptions from storage
- Formats for LLM input

**update**: Update stale descriptions
- Regenerates only stale entries
- Updates database and `.lod` files

**clean**: Clean all code-lod data
- Removes `.code-lod` directory
- Removes all `.lod` files

**config**: Configuration management
- View and edit configuration
- Set provider and model options

**hooks**: Git hooks management
- install: Install pre-commit hook
- uninstall: Remove installed hooks

### SHOULD

- Commands SHOULD support common options (verbose, quiet, etc.)
- Commands SHOULD provide helpful output for success and failure cases

### MAY

- The system MAY add additional commands in the future
- The system MAY support shell completion for commands

## Implementation

### CLI Structure

```
cli/
├── __init__.py      # Main app registration
├── init.py          # Initialize code-lod
├── generate.py      # Generate descriptions
├── status.py        # Check freshness
├── validate.py      # Validate descriptions
├── read.py          # Output descriptions
├── update.py        # Update stale descriptions
├── clean.py         # Clean all data
├── config.py        # Configuration management
└── hooks.py         # Git hooks
```

### Main App (`cli/__init__.py`)

- Creates the main Typer app
- Registers all sub-commands
- Provides top-level help and version info

### Command Pattern

Each command module:
- Defines one or more Typer functions
- Uses `get_paths()` to find project root
- Handles errors with appropriate exit codes
- Provides user-friendly output via `typer.echo()`
