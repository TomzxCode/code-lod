# Code LoD

Code description targeted for LLMs.

Code LoD (Levels of Detail) is a CLI tool that generates, manages, and updates detailed descriptions of code entities such as functions, classes, modules, packages, and projects. By leveraging LLMs and AST-based change detection, Code LoD provides multi-level descriptions that help LLMs understand codebases more effectively.

## Features

- **Multi-language support**: Parses 20+ languages via tree-sitter
- **AST-based hashing**: Detects semantic changes, ignores cosmetic formatting
- **Staleness tracking**: Knows exactly which descriptions need updating
- **Revert detection**: Recognizes when code reverts to a previous version
- **Git hooks**: Pre-commit integration to ensure descriptions stay fresh
- **LLM-consumable output**: Export descriptions in text, JSON, or markdown

## Installation

```bash
uv add code-lod
```

## Quick Start

```bash
# Initialize in your project
code-lod init

# Generate descriptions
code-lod generate

# Check status
code-lod status

# Output for LLM consumption
code-lod read --format json
```

## Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize code-lod in the current directory |
| `generate` | Generate descriptions for code entities |
| `status` | Show freshness status of descriptions |
| `validate` | Validate description freshness |
| `update` | Update stale descriptions |
| `read` | Output descriptions in LLM-consumable format |
| `install-hook` | Install git pre-commit hook |
| `clean` | Remove all code-lod data |

## Architecture

Code LoD uses a dual storage system:

1. **SQLite database** (`hash_index.db`) - Stores metadata, hashes, and descriptions with staleness tracking (should not be version controlled)
2. **`.lod` files** - Structured comment files alongside source code with `@lod` annotations

Descriptions are organized by hierarchical scope: `project` > `package` > `module` > `class` > `function`.

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```

## License

MIT
