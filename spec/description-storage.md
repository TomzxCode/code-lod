# Description Storage

## Overview

The description storage feature provides a dual storage system for code descriptions: a SQLite database for metadata and caching, and `.lod` files alongside source code with structured `@lod` comments for human readability.

## Requirements

### MUST

- The system MUST maintain a SQLite database at `.code-lod/hash-index.db` for hash-to-description mapping
- The database MUST store: hash, description, stale status, created_at, updated_at, and hash_history
- The system MUST create `.lod` files alongside source files to store descriptions
- `.lod` files MUST use structured `@lod` comments with hash, stale status, and description
- The system MUST support reading and writing `.lod` files
- The system MUST parse `@lod` comments to extract hash, stale, and description fields
- The database MUST support CRUD operations: get, set, mark_stale, mark_fresh, delete
- Database connections MUST use context managers for proper cleanup

### SHOULD

- `.lod` files SHOULD include function/class signatures for readability
- `.lod` files SHOULD preserve module-level descriptions
- The writer SHOULD format comments appropriately for the programming language

### MAY

- The system MAY support additional storage backends in the future
- The system MAY compress descriptions in the database for large codebases

## Implementation

### SQLite Database (HashIndex)

Table schema:
```sql
CREATE TABLE descriptions (
    hash TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    stale BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hash_history TEXT DEFAULT '[]'
)
```

Operations:
- `get(hash_)`: Retrieve a description record
- `set(hash_, description, stale, hash_history)`: Create or update a record
- `mark_stale(hash_)`: Mark a description as stale
- `mark_fresh(hash_)`: Mark a description as fresh
- `get_all_stale()`: Retrieve all stale records
- `delete(hash_)`: Remove a record

### .lod Files

Structure:
- Module-level description at the top (optional)
- Entity descriptions with `@lod` annotations

Comment format:
```
# @lod hash:sha256:<hexdigest> stale:true/false
# @lod description:<description text>
<class_or_function_signature>
```

### LodReader

Parses `.lod` files and extracts:
- Scope (function, class, module)
- Name
- Hash, stale status, description
- Signature
- Line numbers

### LodWriter

Writes `.lod` files with:
- Module description header
- Entity descriptions with signatures
- Language-appropriate comment syntax
