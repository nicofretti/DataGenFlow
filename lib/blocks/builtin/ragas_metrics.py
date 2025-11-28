import json
import logging
from typing import Any

from lib.blocks.base import BaseBlock

logger = logging.getLogger(__name__)


class RagasMetrics(BaseBlock):
    name = "Ragas Metrics"
    description = (
        "Evaluate RAG systems using ragas metrics: Context Precision, Context Recall, "
        "Context Entities Recall, Noise Sensitivity, Response Relevancy, Faithfulness"
    )
    category = "metrics"
    inputs = []
    outputs = ["ragas_score"]

    _config_enums = {
        "metric_type": [
            "answer_relevancy",
            "context_precision",
        ]
    }

    _config_descriptions = {
        "metric_type": "Type of ragas metric to calculate",
        "fields": (
            "Field mappings as JSON object. Map ragas field names to your pipeline field names. "
            'Example: {"question": "question", "answer": "answer", "contexts": "chunk_text", '
            '"ground_truth": "ground_truth"}. Only include fields needed for your selected metric.'
        ),
    }

    def __init__(
        self,
        metric_type: str = "faithfulness",
        fields: dict[str, str] | str | None = None,
    ):
        """
        Args:
            metric_type: Type of ragas metric to calculate
            fields: Field mappings dict or JSON string mapping ragas fields to pipeline fields
                   Example: {"question": "question", "answer": "answer", "contexts": "contexts"}
        """
        self.metric_type = metric_type

        # parse fields if string
        if isinstance(fields, str):
            try:
                self.fields = json.loads(fields)
            except json.JSONDecodeError:
                logger.error(f"failed to parse fields as json: {fields}")
                self.fields = {}
        else:
            self.fields = fields or {}

    def _normalize_contexts(self, contexts: Any) -> list[str]:
        """convert contexts to list of strings"""
        if isinstance(contexts, str):
            # try to parse as json array first
            try:
                parsed = json.loads(contexts)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
            # treat as single context
            return [contexts]
        elif isinstance(contexts, list):
            return [str(item) for item in contexts]
        return []

    def _get_metric_inputs(self, data: dict[str, Any]) -> dict[str, Any]:
        """extract and validate required inputs for the metric"""
        inputs = {}

        # get values from data using field mappings
        for ragas_field, pipeline_field in self.fields.items():
            value = data.get(pipeline_field, "")

            # normalize contexts to list of strings
            if ragas_field == "contexts":
                value = self._normalize_contexts(value)

            inputs[ragas_field] = value

        return inputs

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            from ragas import SingleTurnSample
            from ragas.metrics import (
                AnswerRelevancy,
                ContextPrecision,
            )
            from langchain_community.chat_models import ChatOllama
            from langchain_community.embeddings import OllamaEmbeddings
        except ImportError as e:
            logger.error(f"ragas or langchain not installed: {e}")
            return {"ragas_score": 0.0}

        # configure LLM and embeddings for ragas
        try:
            from app import llm_config_manager

            llm_config = await llm_config_manager.get_llm_model(None)

            # create langchain LLM instance
            if llm_config.provider.value == "ollama":
                base_url = (
                    llm_config.endpoint.replace("/v1/chat/completions", "")
                    if llm_config.endpoint
                    else "http://localhost:11434"
                )

                llm = ChatOllama(
                    model=llm_config.model_name,
                    base_url=base_url,
                    temperature=0.0,  # more deterministic for structured output
                    format="json",  # request JSON format from ollama
                )

                # configure embeddings (use nomic-embed-text for ollama)
                embeddings = OllamaEmbeddings(
                    model="nomic-embed-text",
                    base_url=base_url,
                )
            else:
                logger.error(
                    f"unsupported LLM provider for ragas: {llm_config.provider}"
                )
                return {"ragas_score": 0.0}
        except Exception as e:
            logger.error(f"failed to configure LLM for ragas: {e}")
            return {"ragas_score": 0.0}

        # get inputs
        inputs = self._get_metric_inputs(data)

        # select metric and configure with LLM and embeddings
        metric_map = {
            "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
            "context_precision": ContextPrecision(llm=llm),
        }

        metric = metric_map.get(self.metric_type)
        if not metric:
            logger.error(f"unknown metric type: {self.metric_type}")
            return {"ragas_score": 0.0}

        # validate required fields for metric
        if not self._validate_inputs(inputs):
            logger.error(
                f"missing required fields for {self.metric_type}. "
                f"Received: question={bool(inputs.get('question'))}, "
                f"answer={bool(inputs.get('answer'))}, "
                f"contexts={inputs.get('contexts', [])}, "
                f"ground_truth={bool(inputs.get('ground_truth'))}"
            )
            return {"ragas_score": 0.0}

        try:
            # create sample with only required fields for this metric
            sample_kwargs = {}

            # add fields based on what this metric needs
            if inputs.get("question"):
                sample_kwargs["user_input"] = inputs["question"]
            if inputs.get("answer"):
                sample_kwargs["response"] = inputs["answer"]
            if inputs.get("contexts"):
                sample_kwargs["retrieved_contexts"] = inputs["contexts"]
            if inputs.get("ground_truth"):
                sample_kwargs["reference"] = inputs["ground_truth"]

            sample = SingleTurnSample(**sample_kwargs)

            # calculate metric
            score = await metric.single_turn_ascore(sample)

            return {"ragas_score": float(score)}

        except Exception as e:
            logger.error(f"ragas metric calculation failed: {e}")
            return {"ragas_score": 0.0}

    def _validate_inputs(self, inputs: dict[str, Any]) -> bool:
        """check if required fields are present for the selected metric"""
        # define required fields per metric
        requirements = {
            "answer_relevancy": ["question", "answer"],
            "context_precision": ["question", "contexts", "ground_truth"],
        }

        required = requirements.get(self.metric_type, [])

        for field in required:
            value = inputs.get(field)
            if not value:
                return False
            # contexts must be non-empty list
            if field == "contexts" and not isinstance(value, list):
                return False
            if field == "contexts" and len(value) == 0:
                return False

        return True
