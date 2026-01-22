# LLM Integration

## Overview

The LLM integration feature generates code descriptions using various LLM providers (OpenAI, Anthropic, Ollama). It provides a unified interface for description generation with provider-specific implementations and fallback support.

## Requirements

### MUST

- The system MUST support OpenAI, Anthropic, and Ollama providers
- The system MUST provide a mock generator for testing
- The system MUST auto-detect the provider from environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY)
- Each provider MUST implement the DescriptionGenerator interface
- The generator MUST generate descriptions for functions, classes, and modules
- The generator MUST use scope-specific prompts for different entity types
- The generator MUST truncate source code that exceeds MAX_SOURCE_LENGTH (8192 characters)
- The generator MUST fall back to mock descriptions on API errors

### SHOULD

- The system SHOULD support batch generation for multiple entities
- The system SHOULD accept additional context about the codebase
- The system SHOULD support model configuration per scope (project, package, module, class, function)

### MAY

- The system MAY support additional providers in the future
- The system MAY implement retry logic for API failures
- The system MAY cache generated descriptions to reduce API calls

## Implementation

### DescriptionGenerator Interface

Abstract base defining:
- `generate(entity, context)`: Generate description for a single entity
- `generate_batch(entities, context)`: Generate descriptions for multiple entities

### BaseLLMDescriptionGenerator

Base class for LLM providers:
- Defines DEFAULT_MODEL and MAX_SOURCE_LENGTH
- Implements prompt generation based on entity scope
- Handles source truncation
- Provides fallback to mock on errors

### Provider Implementations

- **AnthropicDescriptionGenerator**: Uses Anthropic Claude API
- **OpenAIDescriptionGenerator**: Uses OpenAI API
- **OllamaDescriptionGenerator**: Uses local Ollama instance
- **MockDescriptionGenerator**: Returns placeholder descriptions for testing

### Prompt Templates

Function prompt:
```
You are a code documentation expert. Generate a clear, concise description of the following function.

Function name: {name}
Language: {language}

Provide a 1-2 sentence description of what this function does, its inputs, and its output.
```

Class prompt:
```
You are a code documentation expert. Generate a clear, concise description of the following class.

Class name: {name}
Language: {language}

Provide a 1-2 sentence description of this class's purpose and key functionality.
```

Module prompt:
```
You are a code documentation expert. Generate a clear, concise description of the following module.

Module name: {name}
Language: {language}

Provide a 2-3 sentence overview of this module's purpose and main exports.
```

### Provider Factory

`get_generator(provider, model)` function:
- Auto-detects provider from environment if not specified
- Returns configured generator instance
- Raises ValueError for unsupported providers
