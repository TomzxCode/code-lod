"""Description generation using LLM."""

import os
from abc import ABC, abstractmethod
from enum import Enum

from code_lod.models import ParsedEntity, Scope


class Provider(str, Enum):
    """LLM provider options."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    MOCK = "mock"  # For testing


class DescriptionGenerator(ABC):
    """Abstract base for description generators."""

    @abstractmethod
    def generate(self, entity: ParsedEntity, context: str | None = None) -> str:
        """Generate a description for an entity.

        Args:
            entity: The code entity to describe.
            context: Additional context about the codebase.

        Returns:
            Generated description text.
        """

    @abstractmethod
    def generate_batch(
        self, entities: list[ParsedEntity], context: str | None = None
    ) -> list[str]:
        """Generate descriptions for multiple entities.

        Args:
            entities: List of code entities to describe.
            context: Additional context about the codebase.

        Returns:
            List of generated descriptions.
        """


class BaseLLMDescriptionGenerator(DescriptionGenerator):
    """Base class for LLM-based description generators."""

    # Subclasses should define these
    DEFAULT_MODEL: str
    MAX_SOURCE_LENGTH = 8192

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        """Initialize the generator.

        Args:
            api_key: API key. If None, reads from provider-specific env var.
            model: Model name to use. If None, uses DEFAULT_MODEL.
        """
        self.model = model or self.DEFAULT_MODEL
        self.client = self._create_client(api_key)

    @abstractmethod
    def _create_client(self, api_key: str | None):
        """Create the API client.

        Args:
            api_key: The API key to use.

        Returns:
            The API client instance.
        """

    @abstractmethod
    def _make_api_request(
        self, prompt: str, source: str, model: str | None = None
    ) -> str:
        """Make the actual API request.

        Args:
            prompt: The formatted prompt.
            source: The source code.
            model: Model name to use. If None, uses self.model.

        Returns:
            The generated description.
        """

    def generate(
        self, entity: ParsedEntity, context: str | None = None, model: str | None = None
    ) -> str:
        """Generate a description for an entity.

        Args:
            entity: The code entity to describe.
            context: Additional context about the codebase.
            model: Override model for this specific generation.

        Returns:
            Generated description text.
        """
        from code_lod.llm.description_generator.mock import (
            MockDescriptionGenerator,
        )

        prompt = self._get_prompt(entity, context)
        source_for_prompt = self._truncate_source(entity.source)

        try:
            return self._make_api_request(prompt, source_for_prompt, model)
        except Exception:
            # Fallback to mock description on error
            return MockDescriptionGenerator().generate(entity)

    def generate_batch(
        self, entities: list[ParsedEntity], context: str | None = None
    ) -> list[str]:
        """Generate descriptions for multiple entities.

        Args:
            entities: List of code entities to describe.
            context: Additional context about the codebase.

        Returns:
            List of generated descriptions.
        """
        return [self.generate(entity, context) for entity in entities]

    def _get_prompt(self, entity: ParsedEntity, context: str | None) -> str:
        """Get the appropriate prompt for an entity.

        Args:
            entity: The code entity.
            context: Additional context.

        Returns:
            The prompt to use.
        """
        base_context = f"\n\nContext: {context}" if context else ""

        if entity.scope == Scope.FUNCTION:
            return (
                _FUNCTION_PROMPT.format(
                    name=entity.name, language=entity.language, source="{source}"
                )
                + base_context
            )
        elif entity.scope == Scope.CLASS:
            return (
                _CLASS_PROMPT.format(
                    name=entity.name, language=entity.language, source="{source}"
                )
                + base_context
            )
        elif entity.scope == Scope.MODULE:
            return (
                _MODULE_PROMPT.format(
                    name=entity.name, language=entity.language, source="{source}"
                )
                + base_context
            )
        else:
            return f"Generate a concise 1-2 sentence description for this {entity.scope.value} named {entity.name} in {entity.language}.{base_context}"

    def _truncate_source(self, source: str) -> str:
        """Truncate source code if too long.

        Args:
            source: The source code.

        Returns:
            Truncated source code.
        """
        if len(source) > self.MAX_SOURCE_LENGTH:
            return source[: self.MAX_SOURCE_LENGTH] + "\n... (truncated)"
        return source


def get_generator(
    provider: Provider | None = None,
    model: str | None = None,
) -> DescriptionGenerator:
    """Get a description generator instance.

    Args:
        provider: The LLM provider to use. If None, detects from environment.
        model: Model name to use. Provider-specific.

    Returns:
        A DescriptionGenerator instance.

    Raises:
        ValueError: If the provider is not supported.
    """
    from code_lod.llm.description_generator.anthropic import (
        AnthropicDescriptionGenerator,
    )
    from code_lod.llm.description_generator.mock import MockDescriptionGenerator
    from code_lod.llm.description_generator.ollama import (
        OllamaDescriptionGenerator,
    )
    from code_lod.llm.description_generator.openai import OpenAIDescriptionGenerator

    if provider is None:
        # Auto-detect from environment
        if os.getenv("ANTHROPIC_API_KEY"):
            provider = Provider.ANTHROPIC
        elif os.getenv("OPENAI_API_KEY"):
            provider = Provider.OPENAI
        else:
            # Default to mock
            provider = Provider.MOCK

    if provider == Provider.MOCK:
        return MockDescriptionGenerator()
    elif provider == Provider.ANTHROPIC:
        return AnthropicDescriptionGenerator(model=model)
    elif provider == Provider.OPENAI:
        return OpenAIDescriptionGenerator(model=model)
    elif provider == Provider.OLLAMA:
        return OllamaDescriptionGenerator(model=model)
    else:
        raise ValueError(f"Provider {provider} not yet implemented")


# Prompt templates for LLM integration
_FUNCTION_PROMPT = """You are a code documentation expert. Generate a clear, concise description of the following function.

Function name: {name}
Language: {language}

Provide a 1-2 sentence description of what this function does, its inputs, and its output."""

_CLASS_PROMPT = """You are a code documentation expert. Generate a clear, concise description of the following class.

Class name: {name}
Language: {language}

Provide a 1-2 sentence description of this class's purpose and key functionality."""

_MODULE_PROMPT = """You are a code documentation expert. Generate a clear, concise description of the following module.

Module name: {name}
Language: {language}

Provide a 2-3 sentence overview of this module's purpose and main exports."""
