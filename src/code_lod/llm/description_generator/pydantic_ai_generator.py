"""Pydantic AI description generator."""

from threading import Lock

from pydantic_ai import Agent

from code_lod.llm.description_generator.generator import (
    BaseLLMDescriptionGenerator,
)

# Fallback model per provider when none is configured.
DEFAULT_MODELS: dict[str, str] = {
    "openai": "openai:gpt-4o",
    "anthropic": "anthropic:claude-sonnet-4-5",
    "ollama": "ollama:llama3.2",
}


class PydanticAIDescriptionGenerator(BaseLLMDescriptionGenerator):
    """Description generator using pydantic-ai for all LLM providers.

    The provider name doubles as the pydantic-ai model prefix. Model names
    are resolved to pydantic-ai model strings, e.g. provider ``anthropic``
    with model ``claude-sonnet-4-5`` becomes ``anthropic:claude-sonnet-4-5``.
    Names that already carry a provider prefix (``openai:gpt-4o``) are used
    as-is.
    """

    DEFAULT_MODEL = DEFAULT_MODELS["openai"]

    def __init__(
        self,
        provider: str,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the generator.

        Args:
            provider: The LLM provider name (any pydantic-ai provider prefix).
            api_key: Unused. pydantic-ai reads credentials from
                provider-specific environment variables (e.g. ANTHROPIC_API_KEY).
            model: Model name to use. If None, uses the provider's default.

        Raises:
            ValueError: If the provider has no known default model and none
                is configured.
        """
        self._provider = provider.lower()
        default_model = DEFAULT_MODELS.get(self._provider)
        if model is None and default_model is None:
            raise ValueError(
                f"Provider '{self._provider}' has no default model. "
                f"Configure one with: code-lod config set-model {self._provider} default <model>"
            )
        super().__init__(api_key=api_key, model=model or default_model)
        self._agents: dict[str, Agent] = {}
        self._agents_lock = Lock()

    def _create_client(self, api_key: str | None) -> None:
        """Create the API client.

        Args:
            api_key: Unused. pydantic-ai manages provider clients internally.

        Returns:
            None. Agents are created lazily per model string.
        """
        return None

    def _resolve_model_string(self, model: str | None) -> str:
        """Resolve a model name to a pydantic-ai model string.

        Args:
            model: Model name for this specific generation. If None, uses
                self.model.

        Returns:
            A pydantic-ai model string like ``anthropic:claude-sonnet-4-5``.
        """
        name = model or self.model
        if ":" in name:
            return name
        return f"{self._provider}:{name}"

    def _get_agent(self, model_string: str) -> Agent:
        """Get a cached Agent for a model string.

        Args:
            model_string: The pydantic-ai model string.

        Returns:
            An Agent bound to the model string.
        """
        with self._agents_lock:
            if model_string not in self._agents:
                self._agents[model_string] = Agent(model_string)
            return self._agents[model_string]

    def _make_api_request(
        self, prompt: str, source: str, model: str | None = None
    ) -> str:
        """Make the LLM API request through pydantic-ai.

        Args:
            prompt: The formatted prompt.
            source: The source code.
            model: Model name to use. If None, uses self.model.

        Returns:
            The generated description.
        """
        agent = self._get_agent(self._resolve_model_string(model))
        result = agent.run_sync(f"{prompt}\n\nSource code:\n```\n{source}\n```")
        return result.output.strip()
