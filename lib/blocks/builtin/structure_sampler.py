import logging
import random
from collections import Counter, defaultdict
from typing import Any

from lib.blocks.base import BaseMultiplierBlock
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import ValidationError

logger = logging.getLogger(__name__)


class StructureSampler(BaseMultiplierBlock):
    name = "Structure Sampler"
    description = "Learn distributions from samples and generate skeleton records"
    category = "seeders"
    inputs = []  # reads from initial state
    outputs = ["*"]  # dynamic based on categorical fields

    _config_descriptions = {
        "target_count": "Number of skeleton records to generate",
        "categorical_fields": "List of categorical field names to sample (e.g., ['plan', 'role'])",
        "numeric_fields": "List of numeric field names for hint generation (e.g., ['storage'])",
        "dependencies": "Field dependencies as {child: [parent1]} (e.g., {'role': ['plan']})",
        "seed": "Random seed for reproducibility (optional)",
    }

    def __init__(
        self,
        target_count: int,
        categorical_fields: list[str],
        numeric_fields: list[str] = [],
        dependencies: dict[str, list[str]] = {},
        seed: int | None = None,
    ):
        self.target_count = target_count
        self.categorical_fields = categorical_fields
        self.numeric_fields = numeric_fields
        self.dependencies = dependencies
        self.seed = seed

        if seed is not None:
            random.seed(seed)

    def _validate_samples(self, samples: list[dict[str, Any]]) -> None:
        """validate samples meet minimum requirements"""
        if not samples:
            raise ValidationError(
                "No samples provided in metadata",
                detail={
                    "required_field": "samples",
                    "hint": "Add 'samples' array to seed metadata",
                },
            )

        if len(samples) < 10:
            logger.warning(
                f"Only {len(samples)} samples provided - statistical accuracy may be low. "
                f"Recommend at least 20 samples for better distribution modeling."
            )

    def _analyze_samples(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        """
        extract statistical patterns from samples

        returns:
        {
            "categorical_probs": {"field": {"value": prob, ...}},
            "conditional_probs": {"field|parent=val": {"value": prob, ...}},
            "numeric_stats": {"field": {"min": x, "max": y, "mean": z}},
            "exemplars": [sample1, sample2, ...]
        }
        """
        profile: dict[str, Any] = {
            "categorical_probs": {},
            "conditional_probs": {},
            "numeric_stats": {},
            "exemplars": [],
        }

        # categorical field distributions
        for field in self.categorical_fields:
            values = [sample.get(field) for sample in samples]
            counts = Counter(values)
            total = sum(counts.values())
            profile["categorical_probs"][field] = {
                value: count / total for value, count in counts.items()
            }

        # conditional probabilities for dependencies
        for child_field, parent_fields in self.dependencies.items():
            if child_field not in self.categorical_fields:
                continue

            # group samples by parent values
            grouped: dict[tuple, list[Any]] = defaultdict(list)
            for sample in samples:
                parent_key = tuple(sample.get(p) for p in parent_fields)
                child_value = sample.get(child_field)
                grouped[parent_key].append(child_value)

            # compute conditional probabilities
            for parent_key, child_values in grouped.items():
                counts = Counter(child_values)
                total = sum(counts.values())
                probs = {value: count / total for value, count in counts.items()}

                # build key: "child|parent1=val1,parent2=val2"
                parent_str = ",".join(f"{p}={v}" for p, v in zip(parent_fields, parent_key))
                key = f"{child_field}|{parent_str}"
                profile["conditional_probs"][key] = probs

        # numeric field statistics
        for field in self.numeric_fields:
            values = [sample.get(field) for sample in samples if sample.get(field) is not None]
            if values:
                # filter non-numeric
                numeric_values = []
                for v in values:
                    try:
                        numeric_values.append(float(v))
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Non-numeric value {v} in numeric field {field}, skipping"
                        )

                if numeric_values:
                    profile["numeric_stats"][field] = {
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "mean": sum(numeric_values) / len(numeric_values),
                    }

        # select random exemplars
        num_exemplars = min(5, len(samples))
        profile["exemplars"] = random.sample(samples, num_exemplars)

        return profile

    def _topological_sort(self, fields: list[str]) -> list[str]:
        """
        sort fields by dependency order (parents before children)
        uses simple algorithm for flat dependencies
        """
        # build in-degree map
        in_degree = {field: 0 for field in fields}
        for child_field, parent_fields in self.dependencies.items():
            if child_field in in_degree:
                in_degree[child_field] = len(parent_fields)

        # collect fields with no dependencies first
        result = []
        remaining = set(fields)

        while remaining:
            # find fields with no remaining dependencies
            no_deps = [f for f in remaining if in_degree[f] == 0]

            if not no_deps:
                raise ValidationError(
                    "Circular dependency detected in field dependencies",
                    detail={"dependencies": self.dependencies},
                )

            # add to result
            result.extend(sorted(no_deps))  # sort for determinism
            remaining -= set(no_deps)

            # decrease in-degree for children
            for field in no_deps:
                for child_field, parent_fields in self.dependencies.items():
                    if field in parent_fields and child_field in remaining:
                        in_degree[child_field] -= 1

        return result

    def _sample_from_distribution(self, probs: dict[str, float]) -> Any:
        """weighted random choice from probability distribution"""
        if not probs:
            return None

        values = list(probs.keys())
        weights = list(probs.values())
        return random.choices(values, weights=weights, k=1)[0]

    def _generate_skeletons(
        self, profile: dict[str, Any], count: int
    ) -> list[dict[str, Any]]:
        """
        generate N skeleton records by sampling from learned distributions

        each skeleton contains:
        - all categorical fields (sampled values)
        - _hints field (numeric ranges, exemplars for LLM)
        """
        results = []
        field_order = self._topological_sort(self.categorical_fields)

        for _ in range(count):
            skeleton: dict[str, Any] = {}

            # sample categorical values in dependency order
            for field in field_order:
                if field in self.dependencies:
                    # conditional sampling
                    parent_fields = self.dependencies[field]
                    parent_values = tuple(skeleton.get(p) for p in parent_fields)
                    parent_str = ",".join(f"{p}={v}" for p, v in zip(parent_fields, parent_values))
                    key = f"{field}|{parent_str}"

                    if key in profile["conditional_probs"]:
                        probs = profile["conditional_probs"][key]
                    else:
                        # fallback to marginal distribution
                        logger.warning(
                            f"Unseen combination {key}, using marginal distribution for {field}"
                        )
                        probs = profile["categorical_probs"].get(field, {})

                else:
                    # independent sampling
                    probs = profile["categorical_probs"].get(field, {})

                skeleton[field] = self._sample_from_distribution(probs)

            # generate hints for numeric fields
            hints: dict[str, Any] = {}

            for field in self.numeric_fields:
                if field in profile["numeric_stats"]:
                    stats = profile["numeric_stats"][field]
                    hints[f"{field}_range"] = [stats["min"], stats["max"]]

            # add exemplars that match current categorical values
            matching_exemplars = [
                ex
                for ex in profile["exemplars"]
                if all(ex.get(f) == skeleton.get(f) for f in self.categorical_fields)
            ]

            if not matching_exemplars:
                # use any exemplars
                matching_exemplars = profile["exemplars"][:3]

            hints["exemplars"] = matching_exemplars

            skeleton["_hints"] = hints
            results.append(skeleton)

        return results

    async def execute(self, context: BlockExecutionContext) -> list[dict[str, Any]]:  # type: ignore[override]
        # read samples from initial state
        samples = context.get_state("samples", [])

        # validate samples
        self._validate_samples(samples)

        # analyze samples (internal stats modeling)
        logger.info(f"Analyzing {len(samples)} samples for distribution patterns")
        profile = self._analyze_samples(samples)

        # generate skeletons
        logger.info(f"Generating {self.target_count} skeleton records")
        skeletons = self._generate_skeletons(profile, self.target_count)

        logger.info(
            f"Successfully generated {len(skeletons)} skeletons with "
            f"{len(self.categorical_fields)} categorical fields"
        )

        return skeletons
