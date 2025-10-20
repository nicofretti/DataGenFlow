import random
from lib.blocks.base import BaseBlock
from lib.metrics.difficulty_metrics import DifficultyMetrics

class AdversarialPerturbationBlock(BaseBlock):
    name = "Adversarial Perturbation"
    description = "Generate edge cases with controlled perturbations (Belinkov & Bisk, 2018)"
    inputs = ["conversation"]
    outputs = ["perturbed_conversation", "difficulty_score", "perturbations_applied", "paper"]
    algorithm = "adversarial_perturbation"
    paper = "Belinkov & Bisk, 2018 - Synthetic and Natural Noise Both Break Neural Machine Translation"

    def __init__(self, perturbation_type: str = "realistic_noise", intensity: float = 0.5):
        self.perturbation_type = perturbation_type
        self.intensity = intensity  # 0-1 scale

    async def execute(self, data: dict) -> dict:
        """
        adversarial perturbation algorithm:
        1. select perturbation type
        2. apply with controlled intensity
        3. measure resulting difficulty
        """
        conversation = data.get("conversation", "")

        perturbations = []
        perturbed = conversation

        if self.perturbation_type == "realistic_noise":
            perturbed, perturbations = self._add_realistic_noise(conversation)
        elif self.perturbation_type == "context_shift":
            perturbed, perturbations = self._shift_context(conversation)
        elif self.perturbation_type == "contradiction":
            perturbed, perturbations = self._add_contradiction(conversation)

        difficulty = DifficultyMetrics.compute_difficulty_score(perturbed, perturbations)

        return {
            "perturbed_conversation": perturbed,
            "difficulty_score": difficulty,
            "perturbations_applied": perturbations,
            "paper": "Belinkov & Bisk, 2018 - Synthetic and Natural Noise Both Break Neural Machine Translation"
        }

    def _add_realistic_noise(self, text: str) -> tuple[str, list]:
        """add typos, word order changes, etc."""
        perturbations = []
        words = text.split()

        num_changes = max(1, int(len(words) * self.intensity * 0.1))
        for _ in range(num_changes):
            idx = random.randint(0, len(words) - 1)
            word = words[idx]

            if len(word) > 2:
                # typo
                typo_idx = random.randint(0, len(word) - 1)
                typo_word = word[:typo_idx] + random.choice('abcdefghijklmnopqrstuvwxyz') + word[typo_idx+1:]
                words[idx] = typo_word
                perturbations.append(f"typo_at_{idx}")

        return " ".join(words), perturbations

    def _shift_context(self, text: str) -> tuple[str, list]:
        """change topic midway"""
        perturbations = ["context_shift"]
        # simple: add a random topic shift
        topics = ["billing", "technical", "account", "general"]
        shift = f" [Topic shift: {random.choice(topics)}]"
        return text + shift, perturbations

    def _add_contradiction(self, text: str) -> tuple[str, list]:
        """add contradictory statements"""
        perturbations = ["contradiction_added"]
        contradiction = " But actually, the opposite is true."
        return text + contradiction, perturbations
