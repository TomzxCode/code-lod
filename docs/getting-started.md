# Getting Started

## Installation

### For users

```bash
uv add code-lod
```

### For development

```bash
git clone https://github.com/tomzx/code-lod
cd code-lod
uv sync
```

## Initialization

Initialize Code LoD in your project directory:

```bash
code-lod init
```

This creates:

```
your-project/
├── .code-lod/
│   ├── config.json          # Project configuration
│   ├── hash-index.db        # SQLite database (not version controlled)
│   └── .lod/                # Description files (version controlled)
└── ...
```

### Language support

By default, Code LoD supports Python. Specify additional languages:

```bash
code-lod init --language python --language javascript --language go
```

Supported languages include: Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, C#, Ruby, PHP, Swift, Kotlin, and more.

## LLM Provider Configuration

Code LoD supports multiple LLM providers for generating descriptions. Set up your preferred provider:

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
code-lod config set-model --provider openai --model gpt-4o
```

### Anthropic Claude

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
code-lod config set-model --provider anthropic --model claude-sonnet
```

### Ollama (Local Models)

```bash
# Ensure Ollama is running locally
code-lod config set-model --provider ollama --model codellama
```

### Mock (Testing)

No API key required:

```bash
code-lod config set-model --provider mock
```

### Auto-Detection

If you don't configure a provider, Code LoD automatically detects from environment variables:
- `ANTHROPIC_API_KEY` → uses Anthropic
- `OPENAI_API_KEY` → uses OpenAI
- None found → uses Mock (no API required)

### Scope-Specific Models

Configure different models for different scopes:

```bash
# Use a faster model for functions
code-lod config set-model --scope function --provider openai --model gpt-4o

# Use a more capable model for project-level descriptions
code-lod config set-model --scope project --provider anthropic --model claude-sonnet
```

## Generating Descriptions

### Basic generation

```bash
code-lod generate
```

This scans all source files in the current directory, extracts code entities, and generates descriptions for any new or changed code.

### Generate for a specific path

```bash
code-lod generate src/
```

### Force regeneration

```bash
code-lod generate --force
```

Regenerates all descriptions, even if they're up-to-date.

### Generate for specific scope

```bash
code-lod generate --scope module
```

Scope levels: `project`, `package`, `module`, `class`, `function`

## Checking Status

### View all descriptions

```bash
code-lod status
```

Output:
```
[module] auth.py
  Provides authentication and session management.
[function] authenticate_user
  Authenticates user credentials and returns session token.
[STALE] function hash_password
  This description needs updating.

Total: 42 | Fresh: 40 | Stale: 2
```

### View only stale descriptions

```bash
code-lod status --stale-only
```

## Validating

Check if all descriptions are fresh:

```bash
code-lod validate
```

Exit with error code if stale descriptions exist:

```bash
code-lod validate --fail-on-stale
```

Useful for CI/CD pipelines.

## Reading Descriptions

### Text output

```bash
code-lod read
```

### JSON output

```bash
code-lod read --format json
```

```json
[
  {
    "scope": "function",
    "name": "authenticate_user",
    "description": "Authenticates user credentials...",
    "stale": false,
    "hash": "sha256:abc123..."
  }
]
```

### Filter by scope

```bash
code-lod read --scope class
```

## Git Hooks

Automatically validate descriptions before commits:

```bash
code-lod install-hook
```

This installs a pre-commit hook that runs `code-lod validate --fail-on-stale`.

Remove the hook:

```bash
code-lod uninstall-hook
```

## Cleaning Up

Remove all Code LoD data:

```bash
code-lod clean
```

Skip confirmation:

```bash
code-lod clean --force
```

## Example Workflow

```bash
# 1. Initialize in a new project
cd my-project
code-lod init

# 2. Generate initial descriptions
code-lod generate

# 3. Check status (should show all fresh)
code-lod status

# 4. Make code changes...
# edit files...

# 5. Check status again (some will be stale)
code-lod status

# 6. Update stale descriptions
code-lod update

# 7. Install git hook for future safety
code-lod install-hook
```
