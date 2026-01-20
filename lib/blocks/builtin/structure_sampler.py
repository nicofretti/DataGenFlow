import logging
import random
from collections import Counter, defaultdict
from typing import Any

from lib.blocks.base import BaseBlock
from lib.blocks.commons.template_utils import (
    normalize_template_param,
    render_and_parse_json,
    validate_string_list,
)
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError, ValidationError
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)


class StructureSampler(BaseBlock):
    name = "Structure Sampler"
    description = "Learn distributions from samples and generate skeleton records"
    category = "seeders"
    inputs = []  # reads from initial state
    outputs = ["skeletons", "_seed_samples"]

    # constants for sampling configuration
    MAX_EXEMPLARS = 5
    MAX_MATCHING_EXEMPLARS = 3

    _config_descriptions = {
        "target_count": (
            "Number of skeleton records to generate. "
            "Can be an integer or Jinja template. Examples: 10 or {{ target_count }}"
        ),
        "categorical_fields": (
            'JSON array or Jinja template. Examples: ["plan", "role"] or '
            "{{ categorical_fields | tojson }}"
        ),
        "numeric_fields": (
            'JSON array or Jinja template. Examples: ["storage"] or '
            "{{ numeric_fields | tojson }} (leave empty for none)"
        ),
        "dependencies": (
            'JSON object or Jinja template. Example: {"role": ["plan"]} or '
            "{{ dependencies | tojson }} (leave empty for none)"
        ),
        "seed": "Random seed for reproducibility (optional)",
    }

    _config_formats = {
        "target_count": "json-or-template",
        "categorical_fields": "json-or-template",
        "numeric_fields": "json-or-template",
        "dependencies": "json-or-template",
    }

    def __init__(
        self,
        target_count: int | str,
        categorical_fields: str | list[str],
        numeric_fields: str | list[str] = "",
        dependencies: str | dict[str, list[str]] = "",
        seed: int | None = None,
    ):
        self.target_count_template = (
            str(target_count) if isinstance(target_count, int) else target_count
        )
        self.categorical_fields_template = normalize_template_param(categorical_fields, list)
        self.numeric_fields_template = (
            normalize_template_param(numeric_fields, list) if numeric_fields else ""
        )
        self.dependencies_template = (
            normalize_template_param(dependencies, dict) if dependencies else ""
        )
        self.seed = seed
        self._rng = random.Random(seed)

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

    def _compute_categorical_distributions(
        self, samples: list[dict[str, Any]]
    ) -> dict[str, dict[Any, float]]:
        """compute probability distributions for categorical fields"""
        distributions: dict[str, dict[Any, float]] = {}
        for field in self.categorical_fields:
            values = [sample.get(field) for sample in samples]
            counts = Counter(values)
            total = sum(counts.values())
            distributions[field] = {value: count / total for value, count in counts.items()}
        return distributions

    def _compute_conditional_probabilities(
        self, samples: list[dict[str, Any]]
    ) -> dict[str, dict[str, float]]:
        """compute conditional probabilities for dependent fields"""
        conditional_probs = {}
        for child_field, parent_fields in self.dependencies.items():
            if child_field not in self.categorical_fields:
                continue

            # group samples by parent values
            grouped: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
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
                conditional_probs[key] = probs

        return conditional_probs

    def _compute_numeric_statistics(
        self, samples: list[dict[str, Any]]
    ) -> dict[str, dict[str, float]]:
        """compute min/max/mean statistics for numeric fields"""
        numeric_stats = {}
        for field in self.numeric_fields:
            values = [sample.get(field) for sample in samples if sample.get(field) is not None]
            if values:
                # filter non-numeric
                numeric_values: list[float] = []
                for v in values:
                    if v is None:
                        continue
                    try:
                        numeric_values.append(float(v))
                    except (ValueError, TypeError):
                        logger.warning(f"Non-numeric value {v} in numeric field {field}, skipping")

                if numeric_values:
                    numeric_stats[field] = {
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "mean": sum(numeric_values) / len(numeric_values),
                    }
        return numeric_stats

    def _select_exemplars(
        self, samples: list[dict[str, Any]], max_count: int | None = None
    ) -> list[dict[str, Any]]:
        """randomly select exemplar samples for reference"""
        if max_count is None:
            max_count = self.MAX_EXEMPLARS
        num_exemplars = min(max_count, len(samples))
        return self._rng.sample(samples, num_exemplars)

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
        return {
            "categorical_probs": self._compute_categorical_distributions(samples),
            "conditional_probs": self._compute_conditional_probabilities(samples),
            "numeric_stats": self._compute_numeric_statistics(samples),
            "exemplars": self._select_exemplars(samples),
        }

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
        return self._rng.choices(values, weights=weights, k=1)[0]

    def _sample_categorical_field(
        self, field: str, skeleton: dict[str, Any], profile: dict[str, Any]
    ) -> Any:
        """sample value for a single categorical field, respecting dependencies"""
        if field in self.dependencies:
            # conditional sampling based on parent values
            parent_fields = self.dependencies[field]
            parent_values = tuple(skeleton.get(p) for p in parent_fields)
            parent_str = ",".join(f"{p}={v}" for p, v in zip(parent_fields, parent_values))
            key = f"{field}|{parent_str}"

            if key in profile["conditional_probs"]:
                probs = profile["conditional_probs"][key]
            else:
                # fallback to marginal distribution
                logger.warning(f"Unseen combination {key}, using marginal distribution for {field}")
                probs = profile["categorical_probs"].get(field, {})
        else:
            # independent sampling
            probs = profile["categorical_probs"].get(field, {})

        return self._sample_from_distribution(probs)

    def _generate_hints(self, skeleton: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        """generate hints for numeric fields and matching exemplars"""
        hints: dict[str, Any] = {}

        # add numeric field ranges
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
            # use any exemplars from the full set
            matching_exemplars = profile["exemplars"][: self.MAX_MATCHING_EXEMPLARS]

        hints["exemplars"] = matching_exemplars
        return hints

    def _generate_skeletons(self, profile: dict[str, Any], count: int) -> list[dict[str, Any]]:
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
                skeleton[field] = self._sample_categorical_field(field, skeleton, profile)

            # add hints for LLM generation
            skeleton["_hints"] = self._generate_hints(skeleton, profile)
            results.append(skeleton)

        return results

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        # render and parse target_count from template
        target_count_rendered = render_template(
            self.target_count_template, context.accumulated_state
        )
        try:
            target_count = int(target_count_rendered.strip())
            if target_count <= 0:
                raise BlockExecutionError(
                    "target_count must be a positive integer",
                    detail={"rendered_value": target_count_rendered, "parsed_value": target_count},
                )
        except ValueError as e:
            raise BlockExecutionError(
                f"target_count must be a valid integer: {str(e)}",
                detail={
                    "template": self.target_count_template,
                    "rendered": target_count_rendered,
                },
            )

        # parse categorical_fields from template
        categorical_fields = render_and_parse_json(
            self.categorical_fields_template,
            context.accumulated_state,
            "categorical_fields",
            expected_type=list,
        )
        validate_string_list(categorical_fields, "categorical_fields")

        # parse numeric_fields from template (optional)
        numeric_fields: list[str] = []
        if self.numeric_fields_template:
            numeric_fields = render_and_parse_json(
                self.numeric_fields_template,
                context.accumulated_state,
                "numeric_fields",
                expected_type=list,
            )
            validate_string_list(numeric_fields, "numeric_fields")

        # parse dependencies from template (optional)
        dependencies: dict[str, list[str]] = {}
        if self.dependencies_template:
            dependencies = render_and_parse_json(
                self.dependencies_template,
                context.accumulated_state,
                "dependencies",
                expected_type=dict,
            )
            # validate structure: dict[str, list[str]]
            for key, value in dependencies.items():
                if not isinstance(key, str):
                    raise BlockExecutionError(
                        "All dependency keys must be strings",
                        detail={"dependencies": dependencies},
                    )
                if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                    raise BlockExecutionError(
                        f"Dependency value for '{key}' must be a list of strings",
                        detail={"dependencies": dependencies},
                    )

        # store parsed values for use in methods
        self.categorical_fields = categorical_fields
        self.numeric_fields = numeric_fields
        self.dependencies = dependencies

        # read samples from initial state
        samples = context.get_state("samples", [])

        # validate samples
        self._validate_samples(samples)

        # analyze samples (internal stats modeling)
        logger.info(f"Analyzing {len(samples)} samples for distribution patterns")
        profile = self._analyze_samples(samples)

        # generate skeletons
        logger.info(f"Generating {target_count} skeleton records")
        skeletons = self._generate_skeletons(profile, target_count)

        logger.info(
            f"Successfully generated {len(skeletons)} skeletons with "
            f"{len(self.categorical_fields)} categorical fields"
        )

        # preserve original samples for duplicate checking downstream
        return {"skeletons": skeletons, "_seed_samples": samples}
