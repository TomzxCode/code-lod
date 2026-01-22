# Staleness Tracking

## Overview

The staleness tracking feature monitors when code descriptions need regeneration by comparing current AST hashes against stored hashes. It enables efficient update workflows by identifying only the entities that have changed.

## Requirements

### MUST

- The tracker MUST compare current entity hashes against stored hashes to determine staleness
- An entity MUST be considered stale if no description exists for its hash
- An entity MUST be considered stale if its record is marked as stale in the database
- An entity MUST be considered fresh if a non-stale description exists for its hash
- The tracker MUST provide a status summary with total, fresh, and stale counts
- The tracker MUST list all stale entries with scope, name, path, and hash information
- The tracker MUST support marking hashes as stale or fresh

### SHOULD

- The tracker SHOULD support batch checking of multiple entities
- The tracker SHOULD provide revert detection via hash_history tracking
- The tracker SHOULD expose methods for getting and setting descriptions

### MAY

- The tracker MAY support incremental staleness checking for large codebases
- The tracker MAY provide filtering by scope or file path

## Implementation

### StalenessTracker

Main class that:
- Uses HashIndex for database operations
- Provides checking methods for single or multiple entities
- Tracks stale entries with full context (scope, name, path, hashes)

### FreshnessStatus

Data class containing:
- `total_entities`: Total number of entities checked
- `fresh_count`: Number of fresh entities
- `stale_count`: Number of stale entities
- `stale_entries`: List of StaleEntry objects

### StaleEntry

Data class for stale entities:
- `scope`: The entity scope
- `name`: Entity name
- `path`: File path
- `current_hash`: Current AST hash
- `stored_hash`: Hash from database (if any)

### Revert Detection

- The `check_revert()` method checks if a current hash matches a historical hash
- Returns `(is_revert, description_if_revert)` tuple
- Allows restoration of previous descriptions when code is reverted
