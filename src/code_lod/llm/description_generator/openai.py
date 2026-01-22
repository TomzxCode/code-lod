"""OpenAI description generator."""

from openai import OpenAI

from code_lod.llm.description_generator.generator import (
    BaseLLMDescriptionGenerator,
)


class OpenAIDescriptionGenerator(BaseLLMDescriptionGenerator):
    """Description generator using OpenAI's API."""

    DEFAULT_MODEL = "gpt-4o"

    def _create_client(self, api_key: str | None):
        """Create the OpenAI client.

        Args:
            api_key: The API key to use.

        Returns:
            The OpenAI client instance.
        """
        return OpenAI(api_key=api_key)

    def _make_api_request(
        self, prompt: str, source: str, model: str | None = None
    ) -> str:
        """Make the OpenAI API request.

        Args:
            prompt: The formatted prompt.
            source: The source code.
            model: Model name to use. If None, uses self.model.

        Returns:
            The generated description.
        """
        response = self.client.chat.completions.create(
            model=model or self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nSource code:\n```\n{source}\n```",
                }
            ],
        )
        return response.choices[0].message.content.strip()
