"""Ollama description generator."""

from ollama import Client

from code_lod.llm.description_generator.generator import (
    BaseLLMDescriptionGenerator,
)


class OllamaDescriptionGenerator(BaseLLMDescriptionGenerator):
    """Description generator using Ollama's local API."""

    DEFAULT_MODEL = "llama3.2"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        host: str | None = None,
    ) -> None:
        """Initialize the Ollama generator.

        Args:
            api_key: Unused (Ollama doesn't require API keys).
            model: Model name to use. If None, uses DEFAULT_MODEL.
            host: Ollama host URL. If None, uses default.
        """
        self._host = host
        super().__init__(api_key=api_key, model=model)

    def _create_client(self, api_key: str | None):
        """Create the Ollama client.

        Args:
            api_key: Unused (Ollama doesn't require API keys).

        Returns:
            The Ollama client instance.
        """
        return Client(host=self._host)

    def _make_api_request(
        self, prompt: str, source: str, model: str | None = None
    ) -> str:
        """Make the Ollama API request.

        Args:
            prompt: The formatted prompt.
            source: The source code.
            model: Model name to use. If None, uses self.model.

        Returns:
            The generated description.
        """
        response = self.client.chat(
            model=model or self.model,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nSource code:\n```\n{source}\n```",
                }
            ],
        )
        return response["message"]["content"].strip()
