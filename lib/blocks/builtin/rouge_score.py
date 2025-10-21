from lib.blocks.base import BaseBlock
from rouge_score import rouge_scorer
from typing import Any


class RougeScore(BaseBlock):
    name = "ROUGE Score"
    description = "Calculate ROUGE score comparing generated text against reference text. Configurable via 'generated_field' and 'reference_field' parameters."
    inputs = []
    outputs = ["rouge_score"]

    _config_enums = {
        "rouge_type": ["rouge1", "rouge2", "rougeL"]
    }

    _field_references = ["generated_field", "reference_field"]

    def __init__(
        self,
        generated_field: str = "assistant",
        reference_field: str = "reference",
        rouge_type: str = "rouge1"
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

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        generated = data.get(self.generated_field, "")
        reference = data.get(self.reference_field, "")

        if not generated or not reference:
            return {"rouge_score": 0.0}

        scores = self.scorer.score(reference, generated)
        # return f-measure by default
        score = scores[self.rouge_type].fmeasure

        return {"rouge_score": score}
