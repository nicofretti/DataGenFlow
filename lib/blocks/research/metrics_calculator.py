from typing import Any

from lib.blocks.base import BaseBlock
from lib.metrics import DiversityMetrics, DifficultyMetrics


class MetricsCalculatorBlock(BaseBlock):
    name = "Metrics Calculator"
    description = "Calculate quality metrics for generated conversations"
    inputs = []  # can work with any data
    outputs = ["metrics", "metrics_summary"]

    def __init__(self, compute: list[str] | None = None) -> None:
        self.compute = compute or ["diversity", "coherence", "difficulty", "engagement"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """compute all requested metrics from accumulated state"""
        metrics = {}

        # get the conversation text (could be "conversation" or "dialogue")
        text = data.get("conversation") or data.get("dialogue", "")

        if "diversity" in self.compute and "diversity_score" in data:
            metrics["diversity"] = data.get("diversity_score", 0)

        if "coherence" in self.compute and text:
            metrics["coherence"] = DiversityMetrics.compute_coherence_score(text)

        if "difficulty" in self.compute:
            metrics["difficulty"] = data.get("difficulty_score", 0)

        if "engagement" in self.compute:
            metrics["engagement"] = self._compute_engagement(text)

        summary = self._create_summary(metrics)

        return {"metrics": metrics, "metrics_summary": summary}

    def _compute_engagement(self, text: str) -> float:
        """simple engagement: presence of questions, exclamations"""
        score = 0.0
        score += text.count("?") * 0.2
        score += text.count("!") * 0.1
        return min(1.0, score)

    def _create_summary(self, metrics: dict[str, float]) -> str:
        """create human-readable summary"""
        parts = []
        for key, value in metrics.items():
            parts.append(f"{key}: {value:.2f}")
        return " | ".join(parts)
