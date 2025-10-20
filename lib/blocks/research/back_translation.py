from typing import Any

from lib.blocks.base import BaseBlock
from lib.generator import Generator
from lib.metrics.diversity_metrics import DiversityMetrics
from models import GenerationConfig


class BackTranslationBlock(BaseBlock):
    name = "Back-Translation Diversity"
    description = "Generate diverse conversation variations using back-translation algorithm (Sennrich et al., 2016)"
    inputs = ["conversation"]
    outputs = ["diverse_conversations", "diversity_score", "algorithm", "paper"]
    algorithm = "back_translation_diversity"
    paper = "Sennrich et al., 2016 - Improving Neural Machine Translation Models with Monolingual Data"

    def __init__(
        self,
        num_variations: int = 2,
        temperature: float = 0.8,
        paraphrase_model: str = "t5"
    ) -> None:
        self.num_variations = num_variations
        self.temperature = temperature
        self.paraphrase_model = paraphrase_model

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Back-translation algorithm:
        1. Original conversation
        2. Translate to intermediate form (paraphrase)
        3. Translate back (regenerate) to create variations
        4. Measure diversity
        """
        original = data.get("conversation", "")

        generator = Generator(
            GenerationConfig(temperature=self.temperature, max_tokens=500)
        )

        variations = []
        for _ in range(self.num_variations):
            paraphrase = await self._paraphrase(original, generator)
            regenerated = await self._regenerate(paraphrase, generator)
            variations.append(regenerated)

        # include original for diversity calculation
        all_texts = [original] + variations
        diversity = DiversityMetrics.compute_diversity_score(all_texts)

        return {
            "diverse_conversations": variations,
            "diversity_score": diversity,
            "algorithm": "back_translation_diversity",
            "paper": "Sennrich et al., 2016 - Improving Neural Machine Translation Models with Monolingual Data"
        }

    async def _paraphrase(self, text: str, generator: Generator) -> str:
        """step 1: paraphrase (intermediate representation)"""
        prompt = f"Paraphrase this conversation concisely:\n\n{text}"
        response = await generator.generate(
            system="You are a helpful assistant that paraphrases text while preserving meaning.",
            user=prompt
        )
        return response

    async def _regenerate(self, paraphrase: str, generator: Generator) -> str:
        """step 2: regenerate from paraphrase (creates variation)"""
        prompt = f"Expand this paraphrase back into a natural conversation:\n\n{paraphrase}"
        response = await generator.generate(
            system="You are a helpful assistant that creates natural conversations.",
            user=prompt
        )
        return response
