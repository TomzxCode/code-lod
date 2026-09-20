"""Tests for the pydantic-ai description generator."""

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from code_lod.llm.description_generator.generator import get_generator
from code_lod.llm.description_generator.mock import MockDescriptionGenerator
from code_lod.llm.description_generator.pydantic_ai_generator import (
    DEFAULT_MODELS,
    PydanticAIDescriptionGenerator,
)
from code_lod.models import CodeLocation, ParsedEntity, Scope


def _make_entity() -> ParsedEntity:
    """Create a sample parsed entity."""
    return ParsedEntity(
        scope=Scope.FUNCTION,
        name="greet",
        location=CodeLocation(path="src/sample.py", start_line=1, end_line=3),
        source="def greet(name):\n    return f'Hello {name}'",
        ast_hash="sha256:abc123",
        language="python",
    )


class TestModelStringResolution:
    """Tests for pydantic-ai model string resolution."""

    def test_prefixes_plain_model_name_with_provider(self) -> None:
        generator = PydanticAIDescriptionGenerator(
            "anthropic", model="claude-sonnet-4-5"
        )
        assert generator._resolve_model_string(None) == "anthropic:claude-sonnet-4-5"

    def test_uses_model_override_for_request(self) -> None:
        generator = PydanticAIDescriptionGenerator("openai", model="gpt-4o")
        assert generator._resolve_model_string("gpt-4o-mini") == "openai:gpt-4o-mini"

    def test_keeps_full_model_string_as_is(self) -> None:
        generator = PydanticAIDescriptionGenerator("openai")
        assert (
            generator._resolve_model_string("anthropic:claude-haiku-4-5")
            == "anthropic:claude-haiku-4-5"
        )

    def test_supports_any_provider_prefix(self) -> None:
        generator = PydanticAIDescriptionGenerator("groq", model="llama-3.3-70b")
        assert generator._resolve_model_string(None) == "groq:llama-3.3-70b"

    def test_normalizes_provider_case(self) -> None:
        generator = PydanticAIDescriptionGenerator(
            "Anthropic", model="claude-sonnet-4-5"
        )
        assert generator._provider == "anthropic"

    def test_falls_back_to_provider_default_model(self) -> None:
        for provider, default in DEFAULT_MODELS.items():
            generator = PydanticAIDescriptionGenerator(provider)
            assert generator.model == default

    def test_raises_for_unknown_provider_without_model(self) -> None:
        with pytest.raises(ValueError, match="no default model"):
            PydanticAIDescriptionGenerator("not-a-provider")

    def test_accepts_unknown_provider_with_model(self) -> None:
        generator = PydanticAIDescriptionGenerator("not-a-provider", model="some-model")
        assert generator._resolve_model_string(None) == "not-a-provider:some-model"

    def test_caches_agent_per_model_string(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        generator = PydanticAIDescriptionGenerator("openai")
        first = generator._get_agent("openai:gpt-4o")
        second = generator._get_agent("openai:gpt-4o")
        assert first is second
        assert generator._get_agent("openai:gpt-4o-mini") is not first


class TestGenerateWithPydanticAI:
    """Green-path tests for generate() through pydantic-ai."""

    def test_generate_returns_model_output(self, monkeypatch) -> None:
        agent = Agent(TestModel())
        monkeypatch.setattr(
            PydanticAIDescriptionGenerator, "_get_agent", lambda self, _: agent
        )
        generator = PydanticAIDescriptionGenerator("anthropic")

        description = generator.generate(_make_entity())

        assert isinstance(description, str)
        assert description


class TestGetGenerator:
    """Tests for the get_generator factory."""

    def test_returns_mock_for_mock_provider(self) -> None:
        assert isinstance(get_generator("mock"), MockDescriptionGenerator)

    @pytest.mark.parametrize(
        "provider,model",
        [
            ("openai", None),
            ("anthropic", None),
            ("ollama", None),
            ("groq", "llama-3.3-70b"),
        ],
    )
    def test_returns_pydantic_ai_generator_for_llm_providers(
        self, provider: str, model: str | None
    ) -> None:
        generator = get_generator(provider, model=model)
        assert isinstance(generator, PydanticAIDescriptionGenerator)
        assert generator._provider == provider

    def test_auto_detects_mock_without_env_keys(self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert isinstance(get_generator(None), MockDescriptionGenerator)

    def test_auto_detects_anthropic_from_env(self, monkeypatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        generator = get_generator(None)
        assert isinstance(generator, PydanticAIDescriptionGenerator)
        assert generator._provider == "anthropic"

    def test_auto_detects_openai_from_env(self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        generator = get_generator(None)
        assert isinstance(generator, PydanticAIDescriptionGenerator)
        assert generator._provider == "openai"
