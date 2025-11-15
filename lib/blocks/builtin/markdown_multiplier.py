from typing import Any

from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

from lib.blocks.base import BaseMultiplierBlock


class MarkdownMultiplierBlock(BaseMultiplierBlock):
    name = "Markdown Chunker"
    description = "Split markdown into chunks using LlamaIndex"
    inputs = ["file_content"]
    outputs = ["chunk_text", "chunk_index"]

    _config_enums = {"parser_type": ["markdown", "sentence"]}

    _config_descriptions = {
        "parser_type": (
            "Chunking strategy: 'markdown' respects structure, 'sentence' splits by sentences"
        ),
        "chunk_size": (
            "Maximum chunk size in tokens (0 disables for markdown, required for sentence)"
        ),
        "chunk_overlap": "Overlap between chunks in tokens",
    }

    def __init__(
        self,
        parser_type: str = "markdown",
        chunk_size: int = 0,
        chunk_overlap: int = 50,
    ):
        self.parser_type = parser_type
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _parse_with_sentence_splitter(self, file_content: str) -> list[Any]:
        """parse content using sentence splitter"""
        parser = SentenceSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        return parser.get_nodes_from_documents([Document(text=file_content)])

    def _parse_with_markdown(self, file_content: str) -> list[Any]:
        """parse content using markdown parser with optional sentence splitting"""
        md_parser = MarkdownNodeParser()
        md_nodes = md_parser.get_nodes_from_documents([Document(text=file_content)])

        if self.chunk_size == 0:
            return md_nodes

        sentence_parser = SentenceSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        final_nodes = []
        for md_node in md_nodes:
            sub_nodes = sentence_parser.get_nodes_from_documents([Document(text=md_node.text)])  # type: ignore[attr-defined]
            final_nodes.extend(sub_nodes)
        return final_nodes

    def _format_nodes(self, nodes: list[Any]) -> list[dict[str, Any]]:
        """format nodes to output dict format"""
        return [{"chunk_text": node.text, "chunk_index": idx} for idx, node in enumerate(nodes)]

    async def execute(self, data: dict[str, Any]) -> list[dict[str, Any]]:  # type: ignore[override]
        file_content = data.get("file_content", "")

        if self.parser_type == "sentence":
            nodes = self._parse_with_sentence_splitter(file_content)
        else:
            nodes = self._parse_with_markdown(file_content)

        return self._format_nodes(nodes)

    @classmethod
    def get_required_fields(cls, config: dict[str, Any]) -> list[str]:
        return ["file_content"]
