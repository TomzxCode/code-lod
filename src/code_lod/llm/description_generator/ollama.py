"""Ollama description generator."""

from ollama import Client

from code_lod.llm.description_generator.generator import (
    BaseLLMDescriptionGenerator,
)


class OllamaDescriptionGenerator(BaseLLMDescriptionGenerator):
    """Description generator using Ollama's local API."""

    MODEL = "llama3.2"

    def __init__(
        self,
        api_key: str | None = None,
        host: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the Ollama generator.

        Args:
            api_key: Unused (Ollama doesn't require API keys).
            host: Ollama host URL. If None, uses default.
            model: Model name. If None, uses default MODEL.
        """
        self._model = model or self.MODEL
        self._host = host
        self.client = self._create_client(api_key)

    def _create_client(self, api_key: str | None):
        """Create the Ollama client.

        Args:
            api_key: Unused (Ollama doesn't require API keys).

        Returns:
            The Ollama client instance.
        """
        return Client(host=self._host)

    def _make_api_request(self, prompt: str, source: str) -> str:
        """Make the Ollama API request.

        Args:
            prompt: The formatted prompt.
            source: The source code.

        Returns:
            The generated description.
        """
        response = self.client.chat(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nSource code:\n```\n{source}\n```",
                }
            ],
        )
        return response["message"]["content"].strip()
