# Configuration Management

## Overview

The configuration management feature handles project configuration, provider settings, and model selection per scope. Configuration is stored in `.code-lod/config.json` and manages paths relative to the project root.

## Requirements

### MUST

- The system MUST store configuration in `.code-lod/config.json`
- The system MUST auto-detect the project root by searching for the `.code-lod` directory
- The configuration MUST support: languages list, auto_update flag, fail_on_stale flag, provider selection, and per-provider model settings
- Model settings MUST support default and scope-specific models (project, package, module, class, function)
- The system MUST provide standard paths: code_lod_dir, lod_dir, config_file, hash_db
- The system MUST validate hash format in `@lod` comments

### SHOULD

- The system SHOULD provide default configuration when config file doesn't exist
- The system SHOULD handle configuration errors gracefully by falling back to defaults
- The system SHOULD allow querying model configuration for specific scopes and providers

### MAY

- The system MAY support additional configuration options in the future
- The system MAY provide configuration validation and schema checking

## Implementation

### Config Model

Pydantic BaseModel with fields:
- `languages`: List of supported languages (default: ["python"])
- `auto_update`: Whether to auto-update descriptions (default: false)
- `fail_on_stale`: Whether to fail validation on stale descriptions (default: false)
- `provider`: LLM provider to use (default: Provider.MOCK)
- `model_settings`: Dict mapping Provider to ModelConfig

### ModelConfig Model

Pydantic BaseModel for per-provider model settings:
- `default`: Default model for the provider
- `project`: Model for PROJECT scope
- `package`: Model for PACKAGE scope
- `module`: Model for MODULE scope
- `class_`: Model for CLASS scope
- `function`: Model for FUNCTION scope
- `get_model_for_scope(scope)`: Method to retrieve model for a specific scope

### Paths Dataclass

Frozen dataclass with path management:
- `root_dir`: Project root directory
- `code_lod_dir`: `.code-lod` directory
- `lod_dir`: `.code-lod/.lod` directory
- `config_file`: `.code-lod/config.json`
- `hash_db`: `.code-lod/hash-index.db`

### Configuration Functions

- `find_project_root(start_path)`: Searches upward for `.code-lod` directory
- `get_paths(root_dir)`: Returns Paths object for the project
- `load_config(paths)`: Loads configuration from file or returns defaults
- `save_config(config, paths)`: Saves configuration to file
- `get_model_for_scope(config, provider, scope)`: Retrieves configured model
