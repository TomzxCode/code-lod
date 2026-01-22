# Hierarchical Scopes

## Overview

The hierarchical scopes feature defines different levels of detail for code descriptions. It supports PROJECT, PACKAGE, MODULE, CLASS, and FUNCTION scopes, with each scope having appropriate prompt templates and model configuration options.

## Requirements

### MUST

- The system MUST support the following scopes: PROJECT, PACKAGE, MODULE, CLASS, FUNCTION
- Scopes MUST be hierarchical (PROJECT > PACKAGE > MODULE > CLASS > FUNCTION)
- Each scope MUST have an associated prompt template for LLM generation
- The system MUST support scope-specific model configuration
- The Scope enum MUST use string values for serialization

### SHOULD

- Prompts SHOULD be tailored to the appropriate level of detail for each scope
- Function descriptions SHOULD be 1-2 sentences
- Class descriptions SHOULD be 1-2 sentences
- Module descriptions SHOULD be 2-3 sentences

### MAY

- The system MAY add additional scopes in the future (e.g., METHOD, BLOCK)
- The system MAY support custom scope definitions

## Implementation

### Scope Enum

String enum with values:
- `PROJECT = "project"`
- `PACKAGE = "package"`
- `MODULE = "module"`
- `CLASS = "class"`
- `FUNCTION = "function"`

### Scope-Specific Prompts

Each scope has a dedicated prompt template:

**FUNCTION**: Concise description of what the function does, its inputs, and outputs.

**CLASS**: Description of the class's purpose and key functionality.

**MODULE**: Overview of the module's purpose and main exports.

**PROJECT/PACKAGE**: High-level description (not yet fully implemented).

### Model Configuration

ModelConfig allows per-scope model selection:
- `default`: Fallback model when no scope-specific model is set
- `project/package/module/class/function`: Scope-specific models
- `get_model_for_scope()`: Method to retrieve the appropriate model

### Scope in ParsedEntity

Each ParsedEntity includes:
- `scope`: The Scope enum value
- Used for prompt selection and model configuration
- Affects description generation style and length
