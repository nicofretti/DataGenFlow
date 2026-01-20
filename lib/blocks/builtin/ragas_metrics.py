import json
import logging
import os
from typing import Any

# disable ragas analytics to prevent SSL errors on shutdown
os.environ["RAGAS_DO_NOT_TRACK"] = "true"

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)

# metric requirements - which fields each metric needs
METRIC_REQUIREMENTS: dict[str, list[str]] = {
    "answer_relevancy": ["question", "answer"],
    "context_precision": ["question", "contexts", "ground_truth"],
    "context_recall": ["question", "contexts", "ground_truth"],
    "faithfulness": ["question", "answer", "contexts"],
}


class RagasMetrics(BaseBlock):
    """evaluate a QA pair using RAGAS metrics"""

    name = "Ragas Metrics"
    description = "Evaluate a QA pair using RAGAS metrics"
    category = "metrics"
    inputs = ["*"]
    outputs = ["ragas_scores"]

    _field_references = [
        "question_field",
        "answer_field",
        "contexts_field",
        "ground_truth_field",
    ]

    _config_descriptions = {
        "model": "LLM model for evaluation (leave empty for default)",
        "embedding_model": "Embedding model for answer_relevancy (leave empty for default)",
        "question_field": "Field containing the question",
        "answer_field": "Field containing the answer",
        "contexts_field": "Field containing contexts (list of strings)",
        "ground_truth_field": "Field containing expected answer",
        "metrics": (
            'JSON array or Jinja template. Available: ["answer_relevancy", "context_precision", '
            '"context_recall", "faithfulness"]. Example: ["faithfulness"] or {{ metrics | tojson }}'
        ),
        "score_threshold": "Minimum score (0.0-1.0) to pass",
    }

    _config_formats = {
        "metrics": "json-or-template",
    }

    def __init__(
        self,
        question_field: str = "question",
        answer_field: str = "answer",
        contexts_field: str = "contexts",
        ground_truth_field: str = "ground_truth",
        metrics: str | list[str] = '["faithfulness"]',
        score_threshold: float = 0.5,
        model: str | None = None,
        embedding_model: str | None = None,
    ):
        self.question_field = question_field
        self.answer_field = answer_field
        self.contexts_field = contexts_field
        self.ground_truth_field = ground_truth_field
        # handle both string (from UI/templates with jinja) and list (from static YAML)
        if isinstance(metrics, list):
            self.metrics_template = json.dumps(metrics)
        else:
            self.metrics_template = metrics
        self.score_threshold = max(0.0, min(1.0, score_threshold))
        self.model_name = model
        self.embedding_model_name = embedding_model

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from lib.blocks.commons import UsageTracker

        # parse metrics from template
        metrics_rendered = render_template(self.metrics_template, context.accumulated_state)
        try:
            metrics_list = json.loads(metrics_rendered)
            if not isinstance(metrics_list, list):
                raise BlockExecutionError(
                    "metrics must be a JSON array",
                    detail={"rendered_value": metrics_rendered},
                )
            if not all(isinstance(m, str) for m in metrics_list):
                raise BlockExecutionError(
                    "All items in metrics must be strings",
                    detail={"metrics": metrics_list},
                )
            metrics = metrics_list
        except json.JSONDecodeError as e:
            raise BlockExecutionError(
                f"metrics must be valid JSON: {str(e)}",
                detail={
                    "template": self.metrics_template,
                    "rendered": metrics_rendered,
                },
            )

        # store parsed metrics for use in other methods
        self.metrics = metrics

        # 1. collect inputs from configured fields
        inputs = {
            "question": context.get_state(self.question_field, ""),
            "answer": context.get_state(self.answer_field, ""),
            "contexts": self._normalize_contexts(context.get_state(self.contexts_field, [])),
            "ground_truth": context.get_state(self.ground_truth_field, ""),
        }

        # 2. basic validation - need at least question and answer
        if not inputs["question"] or not inputs["answer"]:
            logger.warning("missing question or answer")
            return {"ragas_scores": self._empty_scores()}

        # 3. set current trace_id for usage tracking (ragas calls don't pass metadata)
        UsageTracker.set_current_trace_id(context.trace_id)

        try:
            # 4. setup ragas LLM
            try:
                llm = await self._create_ragas_llm(context)
            except Exception as e:
                logger.error(f"failed to create LLM: {e}")
                return {"ragas_scores": self._empty_scores()}

            # 5. setup embeddings if needed
            embeddings = None
            if "answer_relevancy" in self.metrics:
                try:
                    embeddings = await self._create_ragas_embeddings()
                except Exception as e:
                    logger.warning(f"failed to create embeddings, skipping answer_relevancy: {e}")

            # 6. build metrics
            metric_instances = self._build_metrics(llm, embeddings)

            # 7. evaluate (with per-metric validation)
            scores = await self._evaluate(inputs, metric_instances)
        finally:
            # clear trace_id context after ragas calls complete
            UsageTracker.set_current_trace_id(None)

        # 8. get accumulated usage from ragas LLM calls
        usage = UsageTracker.to_pipeline_usage(context.trace_id)

        # 9. check threshold (only on non-zero scores)
        valid_scores = [s for s in scores.values() if s > 0]
        passed = len(valid_scores) > 0 and all(s >= self.score_threshold for s in valid_scores)

        return {
            "ragas_scores": {
                **scores,
                "passed": passed,
            },
            "_usage": usage.model_dump(),
        }

    async def _create_ragas_llm(self, context: BlockExecutionContext) -> Any:
        """create ragas LLM using instructor + litellm adapter"""
        import os

        import instructor
        import litellm
        from ragas.llms import llm_factory

        from app import llm_config_manager

        config = await llm_config_manager.get_llm_model(self.model_name)
        params = llm_config_manager.prepare_llm_call(config, temperature=0.0)
        model = params.pop("model")

        # detect provider from model prefix
        provider = "openai"
        if model.startswith("gemini/"):
            provider = "google"
        elif model.startswith("anthropic/"):
            provider = "anthropic"
        elif model.startswith("ollama/"):
            provider = "ollama"

        # set api key environment variable for litellm
        if params.get("api_key"):
            env_key = f"{provider.upper()}_API_KEY"
            if provider == "google":
                env_key = "GEMINI_API_KEY"
            os.environ[env_key] = params.pop("api_key")

        # create instructor client from litellm.acompletion for async support
        client = instructor.from_litellm(litellm.acompletion)

        # pass remaining params (api_base, etc.) to llm_factory as kwargs
        return llm_factory(
            model=model,
            provider=provider,
            client=client,
            adapter="litellm",
            **params,
        )

    async def _create_ragas_embeddings(self) -> Any:
        """create ragas embeddings using LiteLLMEmbeddings"""
        from ragas.embeddings import LiteLLMEmbeddings

        from app import llm_config_manager

        config = await llm_config_manager.get_embedding_model(self.embedding_model_name)
        params = llm_config_manager._prepare_embedding_call(config, input_text="")

        # fix api_base - remove /embeddings suffix if present (litellm adds it)
        api_base = params.get("api_base")
        if api_base and api_base.endswith("/embeddings"):
            api_base = api_base[: -len("/embeddings")]

        return LiteLLMEmbeddings(
            model=params["model"],
            api_key=params.get("api_key"),
            api_base=api_base,
        )

    def _validate_metric_inputs(
        self,
        metric_name: str,
        inputs: dict[str, Any],
    ) -> tuple[bool, str]:
        """validate inputs for a specific metric

        Returns:
            (is_valid, error_message)
        """
        required = METRIC_REQUIREMENTS.get(metric_name, [])
        missing = []

        for field in required:
            value = inputs.get(field)
            if not value:
                missing.append(field)
            # contexts must be non-empty list
            if field == "contexts" and isinstance(value, list) and len(value) == 0:
                missing.append(field)

        if missing:
            return False, f"{metric_name} requires: {', '.join(missing)}"
        return True, ""

    def _normalize_contexts(self, contexts: Any) -> list[str]:
        """convert contexts to list of strings"""
        if isinstance(contexts, str):
            try:
                parsed = json.loads(contexts)
                if isinstance(parsed, list):
                    return [str(c) for c in parsed]
            except json.JSONDecodeError:
                # if the string is not valid JSON, fall back to treating it as a raw context below
                pass
            return [contexts] if contexts else []
        if isinstance(contexts, list):
            return [str(c) for c in contexts]
        return []

    def _empty_scores(self) -> dict[str, Any]:
        """return empty scores with passed=False"""
        return {metric: 0.0 for metric in self.metrics} | {"passed": False}

    def _build_metrics(self, llm: Any, embeddings: Any) -> dict[str, Any]:
        """build metric instances"""
        from ragas.metrics.collections import (
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )

        available: dict[str, Any] = {
            "faithfulness": Faithfulness(llm=llm),
            "context_precision": ContextPrecision(llm=llm),
            "context_recall": ContextRecall(llm=llm),
        }

        if embeddings:
            available["answer_relevancy"] = AnswerRelevancy(llm=llm, embeddings=embeddings)

        return {k: v for k, v in available.items() if k in self.metrics}

    def _get_metric_params(self, metric_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """get the correct params for each metric type (RAGAS 0.4.x API)"""
        base = {"user_input": inputs["question"]}

        if metric_name == "faithfulness":
            return {**base, "response": inputs["answer"], "retrieved_contexts": inputs["contexts"]}
        elif metric_name == "answer_relevancy":
            return {**base, "response": inputs["answer"]}
        elif metric_name in ("context_precision", "context_recall"):
            return {
                **base,
                "retrieved_contexts": inputs["contexts"],
                "reference": inputs["ground_truth"],
            }
        return base

    async def _evaluate(
        self,
        inputs: dict[str, Any],
        metrics: dict[str, Any],
    ) -> dict[str, float]:
        """evaluate with all selected metrics, validating inputs first"""
        scores: dict[str, float] = {}
        for name, metric in metrics.items():
            # validate inputs for this specific metric
            is_valid, error_msg = self._validate_metric_inputs(name, inputs)
            if not is_valid:
                logger.warning(f"skipping {name}: {error_msg}")
                scores[name] = 0.0
                continue

            try:
                # RAGAS 0.4.x uses ascore() with kwargs, returns result object
                params = self._get_metric_params(name, inputs)
                result = await metric.ascore(**params)
                scores[name] = float(result.value)
            except Exception as e:
                logger.warning(f"metric {name} failed: {e}")
                scores[name] = 0.0

        return scores
