"""Mock description generator for testing."""

from code_lod.models import ParsedEntity, Scope
from code_lod.llm.description_generator.generator import DescriptionGenerator


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
