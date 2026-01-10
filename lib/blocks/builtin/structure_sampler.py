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

    # constants for sampling configuration
    MAX_EXEMPLARS = 5
    MAX_MATCHING_EXEMPLARS = 3

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
        """
        Initialize a StructureSampler with sampling configuration and (optionally) a deterministic RNG seed.
        
        Parameters:
            target_count (int): Number of skeleton records to generate when executed.
            categorical_fields (list[str]): List of categorical field names to learn distributions for and sample.
            numeric_fields (list[str], optional): List of numeric field names to collect simple statistics for. Defaults to [].
            dependencies (dict[str, list[str]], optional): Mapping from child categorical field to a list of its parent field names, used to build conditional distributions. Defaults to {}.
            seed (int | None, optional): If provided, seeds Python's global random generator to make sampling deterministic. Defaults to None.
        """
        self.target_count = target_count
        self.categorical_fields = categorical_fields
        self.numeric_fields = numeric_fields
        self.dependencies = dependencies
        self.seed = seed

        if seed is not None:
            random.seed(seed)

    def _validate_samples(self, samples: list[dict[str, Any]]) -> None:
        """
        Validate that the provided samples are suitable for analysis.
        
        Parameters:
            samples (list[dict[str, Any]]): Sample records used to learn distributions.
        
        Raises:
            ValidationError: If `samples` is empty — indicates missing seed metadata and includes a hint to add a `samples` array.
        
        Notes:
            Logs a warning when fewer than 10 samples are provided because small sample sizes reduce statistical accuracy.
        """
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
    ) -> dict[str, dict[str, float]]:
        """
        Learn marginal probability distributions for the instance's categorical fields from the provided sample records.
        
        Parameters:
            samples (list[dict[str, Any]]): Sequence of sample records. Each record is a mapping of field names to values; missing keys are treated as `None` and counted as a distinct category.
        
        Returns:
            dict[str, dict[str, float]]: Mapping from each categorical field to a dictionary that maps an observed value (including `None`) to its probability for that field. Probabilities for a given field sum to 1.
        """
        distributions = {}
        for field in self.categorical_fields:
            values = [sample.get(field) for sample in samples]
            counts = Counter(values)
            total = sum(counts.values())
            distributions[field] = {value: count / total for value, count in counts.items()}
        return distributions

    def _compute_conditional_probabilities(
        self, samples: list[dict[str, Any]]
    ) -> dict[str, dict[str, float]]:
        """
        Learn conditional probability distributions for categorical child fields conditioned on specified parent field values.
        
        Parameters:
            samples (list[dict[str, Any]]): Collection of sample records used to estimate conditional distributions.
        
        Returns:
            dict[str, dict[str, float]]: A mapping where each key is formatted as "child_field|parent1=val1,parent2=val2" and each value is a dictionary that maps child field values to their conditional probability (probabilities for each key sum to 1).
        """
        conditional_probs = {}
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
                conditional_probs[key] = probs

        return conditional_probs

    def _compute_numeric_statistics(
        self, samples: list[dict[str, Any]]
    ) -> dict[str, dict[str, float]]:
        """
        Compute min, max, and mean for the block's configured numeric fields from the provided samples.
        
        Parameters:
            samples (list[dict[str, Any]]): List of sample records to analyze.
        
        Returns:
            dict[str, dict[str, float]]: Mapping from numeric field name to a dictionary with keys
            `"min"`, `"max"`, and `"mean"` containing the computed statistics. Fields with no
            valid numeric values are omitted.
        """
        numeric_stats = {}
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
                    numeric_stats[field] = {
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "mean": sum(numeric_values) / len(numeric_values),
                    }
        return numeric_stats

    def _select_exemplars(
        self, samples: list[dict[str, Any]], max_count: int | None = None
    ) -> list[dict]:
        """
        Select exemplar samples from the provided list for reference.
        
        Parameters:
            samples (list[dict[str, Any]]): Candidate sample records to choose from.
            max_count (int | None): Maximum number of exemplars to return; when None, defaults to self.MAX_EXEMPLARS.
        
        Returns:
            list[dict]: A list of up to `max_count` exemplar samples chosen without replacement (empty if `samples` is empty).
        """
        if max_count is None:
            max_count = self.MAX_EXEMPLARS
        num_exemplars = min(max_count, len(samples))
        return random.sample(samples, num_exemplars)

    def _analyze_samples(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Learn probability distributions, conditional probabilities, numeric statistics, and exemplar records from input samples for skeleton generation.
        
        Parameters:
            samples (list[dict[str, Any]]): Example records used to estimate distributions and statistics.
        
        Returns:
            dict[str, Any]: Profile containing:
                - "categorical_probs": mapping of categorical field -> {value -> probability}
                - "conditional_probs": mapping of "child_field|parent1=val1,..." -> {value -> probability}
                - "numeric_stats": mapping of numeric field -> {"min": number, "max": number, "mean": number}
                - "exemplars": list of exemplar sample records selected from the input
        """
        return {
            "categorical_probs": self._compute_categorical_distributions(samples),
            "conditional_probs": self._compute_conditional_probabilities(samples),
            "numeric_stats": self._compute_numeric_statistics(samples),
            "exemplars": self._select_exemplars(samples),
        }

    def _topological_sort(self, fields: list[str]) -> list[str]:
        """
        Produce an ordering of the given fields such that any parent fields (as defined in self.dependencies) appear before their dependent child fields.
        
        Parameters:
            fields (list[str]): The set of field names to order.
        
        Returns:
            list[str]: A list of the input field names sorted so that parents precede their children. The ordering is deterministic for fields without remaining dependencies.
        
        Raises:
            ValidationError: If the dependencies contain a cycle that prevents a valid ordering.
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
        """
        Sample a single value according to a discrete probability distribution.
        
        Parameters:
            probs (dict[str, float]): Mapping from candidate values to their non-negative weights or probabilities. Values need not sum to 1.
        
        Returns:
            Any: One sampled value according to the provided weights, or `None` if `probs` is empty.
        """
        if not probs:
            return None

        values = list(probs.keys())
        weights = list(probs.values())
        return random.choices(values, weights=weights, k=1)[0]

    def _sample_categorical_field(
        self, field: str, skeleton: dict[str, Any], profile: dict[str, Any]
    ) -> Any:
        """
        Sample a value for a categorical field, using conditional probabilities if parent values are present.
        
        Parameters:
            field (str): The categorical field to sample.
            skeleton (dict[str, Any]): Partially-built record containing already-sampled parent field values.
            profile (dict[str, Any]): Learned profile containing "categorical_probs" and "conditional_probs".
        
        Returns:
            Any: A sampled category value according to the conditional distribution for the field given the skeleton's parent values,
            or the marginal distribution for the field if no matching conditional distribution exists. Returns `None` if no probabilities are available.
        """
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
                logger.warning(
                    f"Unseen combination {key}, using marginal distribution for {field}"
                )
                probs = profile["categorical_probs"].get(field, {})
        else:
            # independent sampling
            probs = profile["categorical_probs"].get(field, {})

        return self._sample_from_distribution(probs)

    def _generate_hints(
        self, skeleton: dict[str, Any], profile: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create hint metadata for a skeleton, including numeric field ranges and exemplar records that match the skeleton's categorical values.
        
        Parameters:
            skeleton (dict[str, Any]): Partial record containing sampled categorical field values used to match exemplars.
            profile (dict[str, Any]): Analysis profile produced by _analyze_samples containing:
                - "numeric_stats": mapping of numeric field -> {"min": number, "max": number, "mean": number}
                - "exemplars": list of exemplar records (dicts)
        
        Returns:
            dict[str, Any]: A hints mapping that includes:
                - "{field}_range": [min, max] entries for each numeric field present in profile["numeric_stats"]
                - "exemplars": a list of exemplar records that match the skeleton's categorical fields (or a small fallback set)
        """
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

    def _generate_skeletons(
        self, profile: dict[str, Any], count: int
    ) -> list[dict[str, Any]]:
        """
        Generate skeleton records sampled from the learned profile.
        
        Parameters:
            profile (dict[str, Any]): Learned distributions and statistics produced by _analyze_samples.
            count (int): Number of skeleton records to generate.
        
        Returns:
            list[dict[str, Any]]: A list of skeleton dictionaries. Each skeleton contains the configured categorical fields with sampled values and an "_hints" entry (numeric ranges and exemplar references).
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

    async def execute(self, context: BlockExecutionContext) -> list[dict[str, Any]]:  # type: ignore[override]
        # read samples from initial state
        """
        Generate skeleton records by learning distributions and statistics from samples stored in the execution context state.
        
        Reads samples from context state key "samples", validates and analyzes them to build a sampling profile, then produces `target_count` skeleton dictionaries. Each skeleton contains sampled categorical fields (respecting declared dependencies) and a `_hints` entry with numeric ranges and exemplar references.
        
        Returns:
            list[dict[str, Any]]: Generated skeleton records, each containing sampled fields and a `_hints` dictionary.
        
        Raises:
            ValidationError: If the samples are missing or fail validation.
        """
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