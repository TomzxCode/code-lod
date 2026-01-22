"""Anthropic Claude description generator."""

from anthropic import Anthropic

from code_lod.llm.description_generator.generator import (
    BaseLLMDescriptionGenerator,
)


class AnthropicDescriptionGenerator(BaseLLMDescriptionGenerator):
    """Description generator using Anthropic's Claude API."""

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def _create_client(self, api_key: str | None):
        """Create the Anthropic client.

        Args:
            api_key: The API key to use.

        Returns:
            The Anthropic client instance.
        """
        return Anthropic(api_key=api_key)

    def _make_api_request(
        self, prompt: str, source: str, model: str | None = None
    ) -> str:
        """Make the Anthropic API request.

        Args:
            prompt: The formatted prompt.
            source: The source code.
            model: Model name to use. If None, uses self.model.

        Returns:
            The generated description.
        """
        response = self.client.messages.create(
            model=model or self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nSource code:\n```\n{source}\n```",
                }
            ],
        )
        return response.content[0].text.strip()
