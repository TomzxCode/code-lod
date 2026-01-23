# Git Integration

## Overview

The Git integration feature provides pre-commit hooks to ensure code descriptions stay fresh. It automatically validates descriptions before commits, preventing stale code documentation from being committed.

## Requirements

### MUST

- The system MUST support installing pre-commit hooks
- The system MUST support uninstalling hooks
- The installed hook MUST run `code-lod validate --fail-on-stale`
- The hook script MUST be executable (chmod 0o755)
- The hook MUST be installed in `.git/hooks/`
- The system MUST verify that code-lod is initialized before installing hooks
- The system MUST verify that the directory is a git repository before installing hooks

### SHOULD

- The system SHOULD support additional hook types (e.g., pre-push)
- The system SHOULD provide clear error messages when initialization or git repository checks fail

### MAY

- The system MAY support hook customization (e.g., different validation commands)
- The system MAY integrate with other hook managers (e.g., pre-commit framework)

## Implementation

### install_hook Function

Creates a git hook script:
1. Validates code-lod is initialized (checks for `.code-lod` directory)
2. Validates the directory is a git repository (checks for `.git/hooks`)
3. Creates the hook script with appropriate content
4. Sets executable permissions (0o755)
5. Reports success to the user

Hook script template:
```bash
#!/bin/sh
# code-lod {hook_type} hook
code-lod validate --fail-on-stale
```

### uninstall_hook Function

Removes the git hook:
1. Validates code-lod is initialized
2. Removes `.git/hooks/pre-commit` if it exists
3. Reports success or that no hook was found

### Error Handling

- Exits with status code 1 if code-lod is not initialized
- Exits with status code 1 if not in a git repository
- Uses typer.echo() for user-friendly error messages
