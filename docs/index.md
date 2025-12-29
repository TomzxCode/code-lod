# Code LoD

**Code description targeted for LLMs.**

Code LoD (Levels of Detail) is a CLI tool that generates, manages, and updates detailed descriptions of code entities. By leveraging LLMs and AST-based change detection, Code LoD provides multi-level descriptions that help LLMs understand codebases more effectively.

## Why Code LoD?

When working with AI code assistants, providing context about your codebase is crucial. Traditional approaches like:

- **Reading entire files** - Expensive token usage, loss of focus
- **Manual documentation** - Time-consuming, quickly becomes stale
- **Vector embeddings** - Good for search, but don't provide structured understanding

Code LoD solves these problems by:

1. **Automatic description generation** - LLMs generate descriptions at multiple levels of detail
2. **Staleness tracking** - Knows exactly when code changes and descriptions need updating
3. **Hierarchical organization** - Organize by project, package, module, class, and function
4. **Version-controlled** - Descriptions live alongside your code in `.lod` files

## Features

- **Multi-language support**: Parses 20+ languages via tree-sitter
- **AST-based hashing**: Detects semantic changes, ignores cosmetic formatting
- **Staleness tracking**: Knows exactly which descriptions need updating
- **Revert detection**: Recognizes when code reverts to a previous version
- **Git hooks**: Pre-commit integration to ensure descriptions stay fresh
- **LLM-consumable output**: Export descriptions in text, JSON, or markdown

## Quick Start

```bash
# Install
uv add code-lod

# Initialize in your project
code-lod init

# Generate descriptions
code-lod generate

# Check status
code-lod status
```

## How It Works

```
code-lod generate
    ↓
Parse code with tree-sitter
    ↓
Compute AST hashes
    ↓
Check hash index for staleness
    ↓
Generate descriptions for new/changed code
    ↓
Store in SQLite + .lod files
```

## Next Steps

- [Getting Started](getting-started.md) - Installation and basic usage
- [Commands](commands.md) - Complete CLI reference
- [Architecture](architecture.md) - How Code LoD works internally
