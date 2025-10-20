import re

class DifficultyMetrics:
    @staticmethod
    def compute_difficulty_score(text: str, perturbations: list = None) -> float:
        """
        compute difficulty based on:
        - typos/errors
        - contradictions
        - context shifts
        - ambiguity
        """
        score = 0.0

        if perturbations:
            score += len(perturbations) * 0.1

        # check for spelling errors (simple heuristic)
        words = text.split()
        error_count = sum(1 for w in words if len(w) > 3 and not w[0].isupper() and
                         sum(1 for c in w if c in 'aeiou') == 0)
        score += min(0.3, error_count * 0.05)

        # clamp to 0-1
        return min(1.0, score)
