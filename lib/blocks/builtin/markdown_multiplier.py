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
        "parser_type": "Chunking strategy: 'markdown' respects structure, 'sentence' is simpler",
        "chunk_size": "Maximum chunk size in tokens (for sentence parser)",
        "chunk_overlap": "Overlap between chunks in tokens (for sentence parser)",
    }

    def __init__(
        self,
        parser_type: str = "markdown",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        self.parser_type = parser_type
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def execute(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        file_content = data.get("file_content", "")

        if self.parser_type == "markdown":
            parser = MarkdownNodeParser()
        else:
            parser = SentenceSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

        nodes = parser.get_nodes_from_documents([Document(text=file_content)])

        return [
            {
                "chunk_text": node.text,
                "chunk_index": idx,
            }
            for idx, node in enumerate(nodes)
        ]

    @classmethod
    def get_required_fields(cls, config: dict[str, Any]) -> list[str]:
        return ["file_content"]
