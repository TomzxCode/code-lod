"""Tree-sitter based code parser."""

from pathlib import Path

import tree_sitter
from tree_sitter_language_pack import get_language, get_parser as get_ts_parser

from code_lod.hashing import compute_ast_hash
from code_lod.models import CodeLocation, ParsedEntity, Scope
from code_lod.parsers.base import BaseParser


# Map of file extensions to language names
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "c_sharp",
    ".scala": "scala",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
}


def detect_language(path: Path) -> str | None:
    """Detect the programming language from a file path.

    Args:
        path: Path to the file.

    Returns:
        Language name or None if not detected.
    """
    suffix = path.suffix.lower()
    return LANGUAGE_MAP.get(suffix)


def get_parser(language: str) -> "TreeSitterParser":
    """Get a parser for the given language.

    Args:
        language: The language name (e.g., "python", "javascript").

    Returns:
        A TreeSitterParser instance.

    Raises:
        ValueError: If the language is not supported.
    """
    return TreeSitterParser(language)


class TreeSitterParser(BaseParser):
    """Tree-sitter based code parser."""

    # Node types to look for by language
    FUNCTION_NODES: dict[str, list[str]] = {
        "python": ["function_definition", "async_function_definition"],
        "javascript": ["function_declaration", "function_expression", "arrow_function"],
        "typescript": ["function_declaration", "function_expression", "arrow_function"],
        "go": ["function_declaration", "method_declaration"],
        "rust": ["function_item", "method_item"],
        "java": ["method_declaration", "constructor_declaration"],
        "c": ["function_definition"],
        "cpp": ["function_definition"],
        "ruby": ["method", "singleton_method"],
        "php": ["function_definition", "method_declaration"],
    }

    CLASS_NODES: dict[str, list[str]] = {
        "python": ["class_definition"],
        "javascript": ["class_declaration", "class_expression"],
        "typescript": [
            "class_declaration",
            "class_expression",
            "interface_declaration",
        ],
        "go": ["type_declaration"],  # Go uses structs/interfaces
        "rust": ["struct_item", "enum_item", "trait_item", "impl_item"],
        "java": ["class_declaration", "interface_declaration", "enum_declaration"],
        "c": ["struct_specifier"],
        "cpp": ["class_specifier", "struct_specifier"],
        "ruby": ["class"],
        "php": ["class_declaration", "interface_declaration"],
    }

    def __init__(self, language: str) -> None:
        """Initialize the parser.

        Args:
            language: The language name (e.g., "python", "javascript").
        """
        self._language = language
        self._ts_language = get_language(language)
        self._ts_parser = get_ts_parser(language)

    @property
    def language(self) -> str:
        """Return the language name."""
        return self._language

    def parse_file(self, path: Path) -> list[ParsedEntity]:
        """Parse a file and extract code entities.

        Args:
            path: Path to the file to parse.

        Returns:
            List of parsed entities (functions, classes, module-level).
        """
        source = path.read_text()
        source_bytes = source.encode()
        tree = self._ts_parser.parse(source_bytes)

        entities: list[ParsedEntity] = []

        # Add module-level entity
        module_entity = self.parse_module(source, path)
        entities.append(module_entity)

        # Extract functions and classes
        function_types = self.FUNCTION_NODES.get(self._language, [])
        class_types = self.CLASS_NODES.get(self._language, [])

        def traverse(node: tree_sitter.Node, parent_name: str | None = None) -> None:
            if node.type in function_types:
                entity = self._parse_function(node, source_bytes, path, parent_name)
                entities.append(entity)
            elif node.type in class_types:
                entity = self._parse_class(node, source_bytes, path, parent_name)
                entities.append(entity)
                # Traverse inside classes for methods
                for child in node.children:
                    traverse(child, entity.name)

            for child in node.children:
                traverse(child, parent_name)

        traverse(tree.root_node)

        return entities

    def parse_module(self, source: str, path: Path) -> ParsedEntity:
        """Parse a module as a whole.

        Args:
            source: The source code.
            path: Path to the file.

        Returns:
            ParsedEntity representing the module.
        """
        return ParsedEntity(
            scope=Scope.MODULE,
            name=path.stem,
            location=CodeLocation(
                path=str(path), start_line=1, end_line=source.count("\n") + 1
            ),
            source=source,
            ast_hash=compute_ast_hash(source),
            language=self._language,
            parent_name=None,
        )

    def _parse_function(
        self,
        node: tree_sitter.Node,
        source: bytes,
        path: Path,
        parent_name: str | None,
    ) -> ParsedEntity:
        """Parse a function node.

        Args:
            node: The tree-sitter node.
            source: The source code as bytes.
            path: Path to the file.
            parent_name: Name of the parent class (if any).

        Returns:
            ParsedEntity for the function.
        """
        name = self._extract_name(node, source)
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        source_text = source[node.start_byte : node.end_byte].decode()

        return ParsedEntity(
            scope=Scope.FUNCTION,
            name=name,
            location=CodeLocation(
                path=str(path), start_line=start_line, end_line=end_line
            ),
            source=source_text,
            ast_hash=compute_ast_hash(source_text),
            language=self._language,
            parent_name=parent_name,
        )

    def _parse_class(
        self,
        node: tree_sitter.Node,
        source: bytes,
        path: Path,
        parent_name: str | None,
    ) -> ParsedEntity:
        """Parse a class node.

        Args:
            node: The tree-sitter node.
            source: The source code as bytes.
            path: Path to the file.
            parent_name: Name of the parent class (if any).

        Returns:
            ParsedEntity for the class.
        """
        name = self._extract_name(node, source)
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        source_text = source[node.start_byte : node.end_byte].decode()

        return ParsedEntity(
            scope=Scope.CLASS,
            name=name,
            location=CodeLocation(
                path=str(path), start_line=start_line, end_line=end_line
            ),
            source=source_text,
            ast_hash=compute_ast_hash(source_text),
            language=self._language,
            parent_name=parent_name,
        )

    def _extract_name(self, node: tree_sitter.Node, source: bytes) -> str:
        """Extract the name from a node.

        Args:
            node: The tree-sitter node.
            source: The source code as bytes.

        Returns:
            The name of the entity.
        """
        # Try to find a "name" child
        for child in node.children:
            if child.type == "name":
                return source[child.start_byte : child.end_byte].decode()
        # Fallback: try identifier
        for child in node.children:
            if child.type == "identifier":
                return source[child.start_byte : child.end_byte].decode()
        # Last resort: use a generic name
        return f"<unnamed_{node.type}>"
