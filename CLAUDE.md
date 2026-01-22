# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rules

- Always update the `CLAUDE.md`, `README.md`, `docs/`, and `spec/` files when there are significant changes to the codebase or architecture.

## Common Commands

```bash
# Development
uv sync                    # Install dependencies
uv add <package>           # Add a dependency
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run pytest              # Run tests

# CLI (after installation)
code-lod init              # Initialize in project directory
code-lod generate          # Generate descriptions
code-lod status            # Check description freshness
code-lod validate          # Validate descriptions
code-lod update            # Update stale descriptions
code-lod read              # Output descriptions in LLM-consumable format
code-lod config set-model  # Configure LLM models per scope
code-lod install-hook      # Install git pre-commit hook
code-lod clean             # Remove all code-lod data

# Documentation
uv run mkdocs build        # Build documentation
uv run mkdocs serve        # Serve docs locally
```

## Architecture

Code LoD is a CLI tool that generates and manages code descriptions at different levels of detail (LoD) for LLM consumption. The architecture has several key layers:

### Core Flow

1. **Parsing** (`parsers/`): Tree-sitter based parsers extract code entities (functions, classes, modules) with AST hashes. Extend `BaseParser` to add new language support.

2. **Hashing** (`hashing.py`): AST hashes are computed on normalized source to detect semantic changes. Hash format: `sha256:<hexdigest>`.

3. **Staleness Tracking** (`staleness.py`): `StalenessTracker` uses the hash index to determine if descriptions need regeneration.

4. **Generation** (`llm/description_generator/`): LLM provider implementations (OpenAI, Anthropic, Ollama, Mock) with auto-detection from environment variables and scope-specific model selection.

5. **Storage** (`db.py`, `lod_file/`): Dual storage system:
   - SQLite database (`hash_index.db`) for metadata and caching
   - `.lod` files alongside source code with `@lod` structured comments

### Key Models

- `Scope`: Hierarchical levels (PROJECT > PACKAGE > MODULE > CLASS > FUNCTION)
- `ParsedEntity`: Extracted code entity with location, source, and ast_hash
- `DescriptionRecord`: Database record with hash, description, staleness, and hash_history

### Directory Structure

```
src/code_lod/
├── cli/                # Typer CLI commands (one file per command)
│   ├── __init__.py     # Main app entry point
│   ├── clean.py        # Clean all code-lod data
│   ├── config.py       # Configuration management (config, set-model commands)
│   ├── generate.py     # Generate descriptions
│   ├── hooks.py        # Git hooks installation/removal
│   ├── init.py         # Initialize code-lod
│   ├── read.py         # Output descriptions
│   ├── status.py       # Check freshness status
│   ├── update.py       # Update stale descriptions
│   └── validate.py     # Validate descriptions
├── config.py           # Configuration and paths management
├── db.py               # SQLite hash index
├── hashing.py          # AST hash computation
├── models.py           # Pydantic data models
├── staleness.py        # StalenessTracker
├── llm/
│   ├── __init__.py
│   └── description_generator/  # LLM generator implementations
│       ├── generator.py  # BaseGenerator, Provider enum, get_generator()
│       ├── anthropic.py  # Anthropic Claude provider
│       ├── openai.py     # OpenAI provider
│       ├── ollama.py     # Ollama local models provider
│       └── mock.py       # Mock generator for testing
├── parsers/            # BaseParser, tree-sitter implementations
└── lod_file/           # .lod file read/write/comment parsing
```

### Important Patterns

- **Plugin Architecture**: Parsers and generators use abstract base classes for extensibility
- **Hash-Based Change Detection**: Revert detection via `hash_history` tracking in database
- **Structured Comments**: `.lod` files use `@lod` annotations with hash, stale status, and description
- **Context Managers**: Database connections use `@contextmanager` pattern
- **Frozen Dataclasses**: `CodeLocation` is immutable; `ParsedEntity` is mutable
- **Empty __init__.py**: Do not add code to `__init__.py`

### Configuration

Stored in `.code-lod/config.json`:
- `languages`: List of supported languages
- `provider`: LLM provider (openai, anthropic, ollama, mock)
- `model_settings`: Hierarchical model configuration per scope
  - Supports different models for different scopes (project, package, module, class, function)

Provider auto-detection: Checks `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` environment variables. Falls back to mock if none found.

Paths are resolved relative to project root via `Paths` dataclass.

### Git Hooks

The `install-hook` command creates pre-commit hooks that run `code-lod validate --fail-on-stale` to ensure descriptions stay fresh. Use `uninstall-hook` to remove the hook.

Supports both `pre-commit` and `pre-push` hook types via `--hook-type` option.
