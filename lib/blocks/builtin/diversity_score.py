from difflib import SequenceMatcher
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext


class DiversityScore(BaseBlock):
    name = "Diversity Score"
    description = (
        "Calculate lexical diversity score for text variations. "
        "Configurable via 'field_name' parameter to specify which field to analyze."
    )
    category = "metrics"
    inputs = []
    outputs = ["diversity_score"]

    _field_references = ["field_name"]

    def __init__(self, field_name: str = "assistant"):
        """
        Args:
            field_name: Name of field in accumulated_state to analyze for diversity
        """
        self.field_name = field_name

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        value = context.get_state(self.field_name, "")

        # if list, compare all pairs
        if isinstance(value, list):
            score = self._compute_list_diversity(value)
        else:
            # single text has no diversity
            score = 0.0

        return {"diversity_score": score}

    def _compute_list_diversity(self, texts: list[str]) -> float:
        if len(texts) < 2:
            return 0.0

        scores = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                ratio = SequenceMatcher(None, texts[i], texts[j]).ratio()
                scores.append(1 - ratio)

        return sum(scores) / len(scores) if scores else 0.0
