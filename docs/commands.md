# Command Reference

Complete reference for all Code LoD CLI commands.

## `init`

Initialize Code LoD in the current project directory.

```bash
code-lod init [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--language` | `-l` | `python` | Languages to support (can be specified multiple times) |
| `--force` | `-f` | `false` | Re-initialize even if already initialized |

### Examples

```bash
# Initialize with Python only
code-lod init

# Initialize with multiple languages
code-lod init -l python -l javascript -l go

# Re-initialize existing setup
code-lod init --force
```

### Creates

- `.code-lod/config.json` - Project configuration
- `.code-lod/hash-index.db` - SQLite database
- `.code-lod/.lod/` - Directory for description files

---

## `generate`

Generate descriptions for code entities.

```bash
code-lod generate [OPTIONS] [PATH]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Path to generate descriptions for (default: current directory) |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--scope` | `-s` | `None` | Hierarchical level to generate |
| `--force` | `-f` | `false` | Regenerate even if fresh |

### Scopes

- `project` - Project-level description
- `package` - Package/directory descriptions
- `module` - Module/file descriptions
- `class` - Class descriptions
- `function` - Function/method descriptions

### Examples

```bash
# Generate for current directory
code-lod generate

# Generate for specific path
code-lod generate src/

# Generate only function descriptions
code-lod generate --scope function

# Force regenerate all descriptions
code-lod generate --force
```

### Output

```
Generated 15 descriptions
Skipped 27 existing descriptions
```

---

## `status`

Show status of descriptions.

```bash
code-lod status [OPTIONS] [PATH]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Path to check (default: current directory) |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--stale-only` | | `false` | Only show stale descriptions |

### Examples

```bash
# Show all descriptions
code-lod status

# Show only stale descriptions
code-lod status --stale-only

# Check specific path
code-lod status src/utils
```

### Output

```
[module] auth.py
  Provides authentication and session management.
[function] authenticate_user
  Authenticates user credentials and returns session token.
[STALE] function hash_password
  This description needs updating.

Total: 42 | Fresh: 40 | Stale: 2
```

### Exit Codes

- `0` - All descriptions are fresh
- `1` - Stale descriptions exist

---

## `validate`

Validate description freshness.

```bash
code-lod validate [OPTIONS] [PATH]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Path to validate (default: current directory) |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--fail-on-stale` | | `false` | Exit with error if stale |

### Examples

```bash
# Validate (always succeeds)
code-lod validate

# Validate and fail on stale
code-lod validate --fail-on-stale
```

### Output

```
All descriptions are fresh
```

or

```
Found 3 stale descriptions
```

---

## `update`

Update stale descriptions.

```bash
code-lod update [OPTIONS] [PATH]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Path to update (default: current directory) |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--auto-approve` | `-y` | `false` | Update without confirmation |

### Examples

```bash
# Update with confirmation
code-lod update

# Update without confirmation
code-lod update --auto-approve

# Update specific path
code-lod update src/
```

---

## `read`

Read and output descriptions in LLM-consumable format.

```bash
code-lod read [OPTIONS] [PATH]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Path to read (default: current directory) |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--scope` | `-s` | `None` | Filter by scope |
| `--format` | `-f` | `text` | Output format: `text`, `json`, `markdown` |

### Examples

```bash
# Read all descriptions as text
code-lod read

# Read as JSON
code-lod read --format json

# Read only class descriptions
code-lod read --scope class

# Read as markdown
code-lod read --format markdown
```

---

## `install-hook`

Install git hook for automatic validation.

```bash
code-lod install-hook [OPTIONS]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--hook-type` | `pre-commit` | Type of hook: `pre-commit` or `pre-push` |

### Examples

```bash
# Install pre-commit hook
code-lod install-hook

# Install pre-push hook
code-lod install-hook --hook-type pre-push
```

### Creates

Git hook file at `.git/hooks/<hook-type>` that runs `code-lod validate --fail-on-stale`.

---

## `uninstall-hook`

Remove the git hook.

```bash
code-lod uninstall-hook
```

### Examples

```bash
code-lod uninstall-hook
```

### Output

```
Uninstalled pre-commit hook
```

or

```
No hook found
```

---

## `clean`

Remove all Code LoD data.

```bash
code-lod clean [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--force` | `-f` | `false` | Skip confirmation |

### Examples

```bash
# Clean with confirmation
code-lod clean

# Clean without confirmation
code-lod clean --force
```

### Removes

The entire `.code-lod/` directory including:
- Configuration file
- SQLite database
- All `.lod` description files

---

## `config`

Get or set configuration values.

```bash
code-lod config <KEY> [VALUE]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `KEY` | Configuration key |
| `VALUE` | Configuration value (for 'set' command) |

### Examples

```bash
# Get configuration value
code-lod config languages

# Set configuration value
code-lod config languages python,javascript
```

---

## `config set-model`

Configure LLM models per scope.

```bash
code-lod config set-model [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--scope` | `-s` | `None` | Scope to configure (project, package, module, class, function) |
| `--provider` | `-p` | `None` | LLM provider (openai, anthropic, ollama, mock) |
| `--model` | `-m` | `None` | Model name |

### Provider Options

| Provider | Environment Variable | Default Models |
|----------|---------------------|----------------|
| `openai` | `OPENAI_API_KEY` | gpt-4o, gpt-4-turbo, gpt-3.5-turbo |
| `anthropic` | `ANTHROPIC_API_KEY` | claude-sonnet, claude-haiku, claude-opus |
| `ollama` | (none) | codellama, mistral, llama2, etc. |
| `mock` | (none) | (no API key required) |

### Examples

```bash
# Set model for all scopes
code-lod config set-model --provider openai --model gpt-4o

# Set different models for different scopes
code-lod config set-model --scope function --provider openai --model gpt-4o
code-lod config set-model --scope project --provider anthropic --model claude-sonnet

# Use Ollama for local generation
code-lod config set-model --provider ollama --model codellama

# Use mock for testing (no API key)
code-lod config set-model --provider mock
```

!!! note
    If no provider is specified, Code LoD auto-detects from environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).
