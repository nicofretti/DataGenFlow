from difflib import SequenceMatcher
from typing import List


class DiversityMetrics:
    @staticmethod
    def compute_diversity_score(texts: List[str]) -> float:
        """
        Compute lexical diversity between texts.
        Range: 0 (identical) to 1 (completely different)
        """
        if len(texts) < 2:
            return 0.0

        scores = []
        for i in range(len(texts)):
            for j in range(i+1, len(texts)):
                ratio = SequenceMatcher(None, texts[i], texts[j]).ratio()
                # invert: lower match = higher diversity
                scores.append(1 - ratio)

        return sum(scores) / len(scores) if scores else 0.0

    @staticmethod
    def compute_coherence_score(text: str) -> float:
        """
        Simple coherence: word count and sentence structure.
        Returns 0-1 score.
        """
        sentences = text.split(".")
        if not sentences:
            return 0.0

        avg_words = len(text.split()) / max(len(sentences), 1)
        # coherent text has 10-30 words per sentence on average
        coherence = min(1.0, avg_words / 20)
        return coherence
