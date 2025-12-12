from typing import Any

from rouge_score import rouge_scorer  # type: ignore[import-untyped]

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext


class RougeScore(BaseBlock):
    name = "ROUGE Score"
    description = (
        "Calculate ROUGE score comparing generated text against reference text. "
        "Configurable via 'generated_field' and 'reference_field' parameters."
    )
    category = "metrics"
    inputs = []
    outputs = ["rouge_score"]

    _config_enums = {"rouge_type": ["rouge1", "rouge2", "rougeL"]}

    _field_references = ["generated_field", "reference_field"]

    def __init__(
        self,
        generated_field: str = "assistant",
        reference_field: str = "reference",
        rouge_type: str = "rouge1",
    ):
        """
        Args:
            generated_field: Name of field containing generated text
            reference_field: Name of field containing reference text
            rouge_type: Type of ROUGE metric (rouge1, rouge2, rougeL)
        """
        self.generated_field = generated_field
        self.reference_field = reference_field
        self.rouge_type = rouge_type
        self.scorer = rouge_scorer.RougeScorer([rouge_type], use_stemmer=True)

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        generated = context.get_state(self.generated_field, "")
        reference = context.get_state(self.reference_field, "")

        if not generated or not reference:
            return {"rouge_score": 0.0}

        scores = self.scorer.score(reference, generated)
        # return f-measure by default
        score = scores[self.rouge_type].fmeasure

        return {"rouge_score": score}
