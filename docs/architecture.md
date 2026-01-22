# Architecture

Deep dive into Code LoD's internal architecture and design.

## Overview

Code LoD uses a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLI Interface                              │
│                            (cli.py)                                 │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Core Engine                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ Code Parser     │  │   Hash Engine   │  │  Staleness Tracker  │ │
│  │ (parsers/)      │  │   (hashing.py)  │  │   (staleness.py)    │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────────┘ │
└───────────┼────────────────────┼────────────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Storage Layer                                    │
│  ┌─────────────────┐  ┌─────────────────────┐                       │
│  │ SQLite DB       │  │  .lod Files         │                       │
│  │ (db.py)         │  │  (lod_file/)        │                       │
│  └─────────────────┘  └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM Integration                                  │
│                      (llm/)                                         │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### CLI Layer (`cli/`)

Built with [Typer](https://typer.tiangolo.com/), the CLI provides all user-facing commands. Each command is implemented in its own module:

| Command | Handler | Description |
|---------|---------|-------------|
| `init` | `cli/init.py` | Creates project structure and config |
| `generate` | `cli/generate.py` | Parses code, generates descriptions |
| `status` | `cli/status.py` | Reports freshness status |
| `validate` | `cli/validate.py` | Checks for stale descriptions |
| `update` | `cli/update.py` | Regenerates stale descriptions |
| `read` | `cli/read.py` | Outputs descriptions for LLMs |
| `config` | `cli/config.py` | Get/set configuration values |
| `config set-model` | `cli/config.py` | Configure LLM models per scope |
| `install-hook` | `cli/hooks.py` | Installs git hooks |
| `uninstall-hook` | `cli/hooks.py` | Removes git hooks |
| `clean` | `cli/clean.py` | Removes all code-lod data |

### Parser Layer (`parsers/`)

Code parsers extract entities using tree-sitter.

#### BaseParser Interface

```python
class BaseParser(ABC):
    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language name this parser handles."""

    @abstractmethod
    def parse_file(self, path: Path) -> list[ParsedEntity]:
        """Parse a file and extract code entities."""

    @abstractmethod
    def parse_module(self, source: str, path: Path) -> ParsedEntity:
        """Parse a module as a whole."""
```

#### TreeSitterParser

The default parser uses [tree-sitter](https://tree-sitter.github.io/tree-sitter/) to support 20+ languages:

- Python, JavaScript, TypeScript
- Go, Rust, Java, C, C++, C#
- Ruby, PHP, Swift, Kotlin
- And more...

### Hash Engine (`hashing.py`)

AST-based hashing detects semantic changes while ignoring cosmetic differences.

#### Hash Computation

```python
def compute_ast_hash(source: str) -> str:
    normalized = _normalize_source(source)
    hash_obj = hashlib.sha256(normalized.encode())
    return f"sha256:{hash_obj.hexdigest()}"
```

#### Normalization

The `_normalize_source()` function:

1. Strips comments
2. Normalizes whitespace
3. Normalizes string literals
4. Preserves semantic structure

This ensures that formatting changes don't trigger staleness.

### Staleness Tracker (`staleness.py`)

Tracks which descriptions need updating.

```python
class StalenessTracker:
    def check_entity(self, entity: ParsedEntity) -> StalenessStatus
    def check_entities(self, entities: list[ParsedEntity]) -> FreshnessStatus
    def mark_stale(self, hash_: str) -> None
    def mark_fresh(self, hash_: str) -> None
```

#### Revert Detection

Uses `hash_history` in the database to detect when code reverts to a previous version:

```python
def check_revert(self, current_hash: str) -> tuple[bool, str | None]:
    record = self.hash_index.get(current_hash)
    if record and not record.stale:
        return True, record.description
    return False, None
```

### Storage Layer

#### SQLite Database (`db.py`)

The `HashIndex` provides fast hash-to-description lookup:

```sql
CREATE TABLE descriptions (
    hash TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    stale BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash_history TEXT DEFAULT '[]'
);
```

#### .lod Files (`lod_file/`)

Structured comment files stored alongside source code:

```python
# @lod hash:sha256:a1b2c3d4... stale:false
# @lod description: Provides user authentication functionality.

def authenticate_user(username: str, password: str) -> str:
    ...
```

**Why dual storage?**

- **SQLite**: Fast lookups, caching, revert detection
- **.lod files**: Human-readable, version-controlled, LLM-consumable

### LLM Integration (`llm/description_generator/`)

Abstract interface for description generation with multiple provider implementations:

```python
class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    MOCK = "mock"

def get_generator(
    provider: Provider | None = None,
    model: str | None = None,
) -> DescriptionGenerator:
    """Get a description generator instance."""
```

#### Provider Implementations

**OpenAI** (`openai.py`): GPT-4, GPT-4o, GPT-3.5-turbo via `openai` package

**Anthropic** (`anthropic.py`): Claude Sonnet, Claude Haiku, Claude Opus via `anthropic` package

**Ollama** (`ollama.py`): Local models (codellama, mistral, llama2, etc.) via `ollama` package

**Mock** (`mock.py`): Placeholder descriptions for testing (no API key required)

#### Auto-Detection

The `get_generator()` function auto-detects providers from environment variables:
1. Checks `ANTHROPIC_API_KEY` → uses Anthropic
2. Checks `OPENAI_API_KEY` → uses OpenAI
3. Falls back to Mock generator

#### Scope-Specific Models

Configure different models for different hierarchical scopes:

```bash
code-lod config set-model --scope function --provider openai --model gpt-4o
code-lod config set-model --scope project --provider anthropic --model claude-sonnet
```

#### Base Generator Interface

```python
class DescriptionGenerator(ABC):
    @abstractmethod
    def generate(self, entity: ParsedEntity, context: str | None = None) -> str:
        """Generate a description for a code entity."""

    @abstractmethod
    def generate_batch(self, entities: list[ParsedEntity], context: str | None = None) -> list[str]:
        """Generate descriptions for multiple entities."""
```

The `BaseLLMDescriptionGenerator` provides:
- Prompt templates for function, class, and module scopes
- Source truncation for large code blocks
- Automatic fallback to mock on API errors

## Data Models

### Scope Hierarchy

```python
class Scope(str, Enum):
    PROJECT = "project"      # Entire codebase
    PACKAGE = "package"      # Directory/module group
    MODULE = "module"        # Single file
    CLASS = "class"          # Class definition
    FUNCTION = "function"    # Function/method
```

### ParsedEntity

```python
@dataclass
class ParsedEntity:
    scope: Scope
    name: str
    location: CodeLocation
    source: str
    ast_hash: str
    language: str
    parent_name: str | None = None
```

## File Structure

```
src/code_lod/
├── __init__.py
├── __main__.py         # Entry point
├── cli/                # CLI commands (one per file)
│   ├── __init__.py     # Main app, command registration
│   ├── clean.py        # Clean command
│   ├── config.py       # Config and set-model commands
│   ├── generate.py     # Generate command
│   ├── hooks.py        # install-hook, uninstall-hook
│   ├── init.py         # Init command
│   ├── read.py         # Read command
│   ├── status.py       # Status command
│   ├── update.py       # Update command
│   └── validate.py     # Validate command
├── config.py           # Configuration and paths management
├── db.py               # SQLite database layer
├── hashing.py          # AST hash computation
├── models.py           # Pydantic data models
├── staleness.py        # Staleness tracking
├── llm/                # LLM integration
│   ├── __init__.py
│   └── description_generator/
│       ├── generator.py    # Base classes, Provider enum, get_generator()
│       ├── anthropic.py    # Anthropic Claude provider
│       ├── openai.py       # OpenAI provider
│       ├── ollama.py       # Ollama local models provider
│       └── mock.py         # Mock generator for testing
├── parsers/            # Code parsers
│   ├── __init__.py
│   ├── base.py         # BaseParser interface
│   └── tree_sitter_parser.py
└── lod_file/           # .lod file management
    ├── __init__.py
    ├── comment_parser.py   # Parse @lod comments
    ├── reader.py           # Read .lod files
    └── writer.py           # Write .lod files
```

## Directory Layout

After running `code-lod init`:

```
your-project/
├── .code-lod/
│   ├── config.json          # Project configuration
│   ├── hash-index.db        # SQLite database (not version controlled)
│   └── .lod/                # Description files (version controlled)
│       └── src/
│           └── module.py.lod
└── src/
    └── module.py
```

## Design Principles

1. **Plugin Architecture**: Parsers and generators use abstract base classes for extensibility
2. **Hash-Based Change Detection**: Semantic changes trigger updates, formatting doesn't
3. **Dual Storage**: SQLite for performance, .lod files for portability
4. **Frozen Dataclasses**: Immutable data where possible (`CodeLocation`)
5. **Context Managers**: Safe database connection handling
6. **Structured Logging**: All operations logged via structlog

## Performance Considerations

- **Hash lookups**: O(1) via SQLite primary key
- **Tree-sitter parsing**: Fast, incremental parsing
- **Lazy generation**: Only regenerates stale descriptions
- **Caching**: Database serves as description cache
