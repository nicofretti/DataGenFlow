from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext


class CoherenceScore(BaseBlock):
    name = "Coherence Score"
    description = (
        "Calculate text coherence based on sentence structure. "
        "Configurable via 'field_name' parameter to specify which field to analyze."
    )
    category = "metrics"
    inputs = []
    outputs = ["coherence_score"]

    _field_references = ["field_name"]

    def __init__(self, field_name: str = "assistant"):
        """
        Args:
            field_name: Name of field in accumulated_state to analyze for coherence
        """
        self.field_name = field_name

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        text = context.get_state(self.field_name, "")

        if not text:
            return {"coherence_score": 0.0}

        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if not sentences:
            return {"coherence_score": 0.0}

        # simple coherence: average words per sentence (10-30 is coherent)
        avg_words = len(text.split()) / len(sentences)
        coherence = min(1.0, avg_words / 20)

        return {"coherence_score": coherence}
