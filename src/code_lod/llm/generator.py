"""Description generation using LLM."""

import os
from abc import ABC, abstractmethod
from enum import Enum

from anthropic import Anthropic
from openai import OpenAI
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


class MockDescriptionGenerator(DescriptionGenerator):
    """Mock generator for testing and initial development.

    This generates simple placeholder descriptions without calling an LLM.
    """

    def generate(self, entity: ParsedEntity, context: str | None = None) -> str:
        """Generate a mock description for an entity.

        Args:
            entity: The code entity to describe.
            context: Additional context (ignored).

        Returns:
            Generated description text.
        """
        if entity.scope == Scope.FUNCTION:
            return f"Function {entity.name} in {entity.language}."
        elif entity.scope == Scope.CLASS:
            return f"Class {entity.name} in {entity.language}."
        elif entity.scope == Scope.MODULE:
            return f"Module {entity.name} written in {entity.language}."
        elif entity.scope == Scope.PACKAGE:
            return f"Package {entity.name} containing related modules."
        elif entity.scope == Scope.PROJECT:
            return f"Project at {entity.location.path}."
        else:
            return f"{entity.scope.value} {entity.name}."

    def generate_batch(
        self, entities: list[ParsedEntity], context: str | None = None
    ) -> list[str]:
        """Generate mock descriptions for multiple entities.

        Args:
            entities: List of code entities to describe.
            context: Additional context (ignored).

        Returns:
            List of generated descriptions.
        """
        return [self.generate(entity, context) for entity in entities]


class AnthropicDescriptionGenerator(DescriptionGenerator):
    """Description generator using Anthropic's Claude API."""

    # Model to use for generation
    MODEL = "claude-sonnet-4-5-20250929"

    # Maximum source code length to include in prompts
    MAX_SOURCE_LENGTH = 8192

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the Anthropic generator.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        """
        self.client = Anthropic(api_key=api_key)

    def generate(self, entity: ParsedEntity, context: str | None = None) -> str:
        """Generate a description for an entity.

        Args:
            entity: The code entity to describe.
            context: Additional context about the codebase.

        Returns:
            Generated description text.
        """
        prompt = self._get_prompt(entity, context)
        source_for_prompt = self._truncate_source(entity.source)

        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nSource code:\n```\n{source_for_prompt}\n```",
                    }
                ],
            )
            return response.content[0].text.strip()
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


class OpenAIDescriptionGenerator(DescriptionGenerator):
    """Description generator using OpenAI's API."""

    # Model to use for generation
    MODEL = "gpt-4o"

    # Maximum source code length to include in prompts
    MAX_SOURCE_LENGTH = 8192

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the OpenAI generator.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
        """
        self.client = OpenAI(api_key=api_key)

    def generate(self, entity: ParsedEntity, context: str | None = None) -> str:
        """Generate a description for an entity.

        Args:
            entity: The code entity to describe.
            context: Additional context about the codebase.

        Returns:
            Generated description text.
        """
        prompt = self._get_prompt(entity, context)
        source_for_prompt = self._truncate_source(entity.source)

        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nSource code:\n```\n{source_for_prompt}\n```",
                    }
                ],
            )
            return response.choices[0].message.content.strip()
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


def get_generator(provider: Provider | None = None) -> DescriptionGenerator:
    """Get a description generator instance.

    Args:
        provider: The LLM provider to use. If None, detects from environment.

    Returns:
        A DescriptionGenerator instance.

    Raises:
        ValueError: If the provider is not supported.
    """
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
        return AnthropicDescriptionGenerator()
    elif provider == Provider.OPENAI:
        return OpenAIDescriptionGenerator()
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
