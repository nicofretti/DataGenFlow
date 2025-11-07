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

    async def execute(self, data: dict[str, Any]) -> list[dict[str, Any]]:  # type: ignore[override]
        file_content = data.get("file_content", "")

        if self.parser_type == "sentence":
            parser = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            nodes = parser.get_nodes_from_documents([Document(text=file_content)])
            return [{"chunk_text": node.text, "chunk_index": idx} for idx, node in enumerate(nodes)]  # type: ignore[attr-defined]

        md_parser = MarkdownNodeParser()
        md_nodes = md_parser.get_nodes_from_documents([Document(text=file_content)])

        if self.chunk_size == 0:
            return [
                {"chunk_text": node.text, "chunk_index": idx}  # type: ignore[attr-defined]
                for idx, node in enumerate(md_nodes)
            ]

        sentence_parser = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        final_nodes = []
        for md_node in md_nodes:
            sub_nodes = sentence_parser.get_nodes_from_documents([Document(text=md_node.text)])  # type: ignore[attr-defined]
            final_nodes.extend(sub_nodes)

        return [
            {"chunk_text": node.text, "chunk_index": idx}  # type: ignore[attr-defined]
            for idx, node in enumerate(final_nodes)
        ]

    @classmethod
    def get_required_fields(cls, config: dict[str, Any]) -> list[str]:
        return ["file_content"]
