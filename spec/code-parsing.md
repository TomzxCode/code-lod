# Code Parsing

## Overview

The code parsing feature extracts code entities (functions, classes, modules) from source files using Tree-sitter parsers. It computes AST hashes for each entity to enable change detection and staleness tracking.

## Requirements

### MUST

- The parser MUST extract all functions, classes, and module-level entities from source files
- The parser MUST compute AST hashes for each extracted entity using normalized source code
- The parser MUST support Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, Ruby, PHP, C#, Scala, Bash, YAML, JSON, TOML, and Markdown
- The parser MUST provide a file extension to language name mapping
- The parser MUST detect the programming language from file extensions automatically
- The base parser interface MUST be implemented as an abstract base class
- Each parsed entity MUST include: scope, name, location (path, start_line, end_line), source code, AST hash, language, and optional parent name

### SHOULD

- The parser SHOULD normalize source code before hashing to ignore cosmetic changes (comments, whitespace)
- The parser SHOULD extract parent names for nested entities (methods in classes)
- The parser SHOULD handle language-specific node types for functions and classes

### MAY

- The parser MAY support additional languages via Tree-sitter language pack
- The parser MAY cache parsed entities for performance

## Implementation

### BaseParser Interface

Abstract base class defining:
- `language` property: Returns the language name
- `parse_file(path)`: Parses a file and returns list of ParsedEntity
- `parse_module(source, path)`: Parses a module as a whole

### TreeSitterParser

Concrete implementation using Tree-sitter:
- Maintains language-specific node type mappings for functions and classes
- Traverses the AST to extract entities with proper parent relationships
- Uses tree-sitter-language-pack for dynamic language loading

### Hash Computation

- Normalizes source by stripping comments and normalizing whitespace
- Computes SHA-256 hash prefixed with "sha256:"
- Hashes are used for change detection and staleness tracking
