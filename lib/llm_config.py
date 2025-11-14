import logging
import re
import time
from typing import Any

import litellm

from config import settings
from lib.errors import PipelineError
from lib.storage import Storage
from models import (
    ConnectionTestResult,
    EmbeddingModelConfig,
    LLMModelConfig,
    LLMProvider,
)

logger = logging.getLogger(__name__)


class LLMConfigError(PipelineError):
    """base exception for llm config errors"""

    pass


class LLMConfigNotFoundError(LLMConfigError):
    """raised when requested model config doesn't exist"""

    pass


class LLMConfigManager:
    """centralized manager for llm and embedding configurations"""

    def __init__(self, storage: Storage):
        self.storage = storage

    async def get_llm_model(self, name: str | None = None) -> LLMModelConfig:
        """get llm config by name, or default if name is none

        uses fallback chain to ensure blocks always have a model available:
        1. requested name
        2. model named "default"
        3. first model in db
        4. .env fallback (LLM_ENDPOINT, LLM_API_KEY, LLM_MODEL)
        """
        if name:
            config_dict = await self.storage.get_llm_model(name)
            if config_dict:
                return LLMModelConfig(**config_dict)
            raise LLMConfigNotFoundError(
                f"llm model '{name}' not found", detail={"requested_name": name}
            )

        # try default model
        config_dict = await self.storage.get_llm_model("default")
        if config_dict:
            return LLMModelConfig(**config_dict)

        # try first model
        all_models = await self.storage.list_llm_models()
        if all_models:
            return LLMModelConfig(**all_models[0])

        # fallback to .env
        if settings.LLM_MODEL and settings.LLM_ENDPOINT:
            provider = self._detect_provider_from_endpoint(settings.LLM_ENDPOINT)
            return LLMModelConfig(
                name="env-fallback",
                provider=provider,
                endpoint=settings.LLM_ENDPOINT,
                api_key=settings.LLM_API_KEY if settings.LLM_API_KEY else None,
                model_name=settings.LLM_MODEL,
            )

        raise LLMConfigNotFoundError(
            "no llm models configured and no .env fallback available",
            detail={"checked": ["database", "env"]},
        )

    async def list_llm_models(self) -> list[LLMModelConfig]:
        """list all configured llm models"""
        models_dict = await self.storage.list_llm_models()
        return [LLMModelConfig(**m) for m in models_dict]

    async def save_llm_model(self, config: LLMModelConfig) -> None:
        """create or update llm model config"""
        await self.storage.save_llm_model(config.model_dump())

    async def delete_llm_model(self, name: str) -> None:
        """delete llm model config"""
        success = await self.storage.delete_llm_model(name)
        if not success:
            raise LLMConfigNotFoundError(f"llm model '{name}' not found", detail={"name": name})

    async def test_llm_connection(self, config: LLMModelConfig) -> ConnectionTestResult:
        """test llm connection with simple prompt

        uses minimal test to validate connectivity before saving config
        """
        start_time = time.time()
        try:
            llm_params = self.prepare_llm_call(
                config,
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=10,
                timeout=10,
            )
            await litellm.acompletion(**llm_params)
            latency_ms = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=True, message="connection successful", latency_ms=latency_ms
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=False, message=f"connection failed: {str(e)}", latency_ms=latency_ms
            )

    async def get_embedding_model(self, name: str | None = None) -> EmbeddingModelConfig:
        """get embedding config by name, or default if name is none

        fallback chain:
        1. requested name
        2. model named "default"
        3. first model in db
        """
        if name:
            config_dict = await self.storage.get_embedding_model(name)
            if config_dict:
                return EmbeddingModelConfig(**config_dict)
            raise LLMConfigNotFoundError(
                f"embedding model '{name}' not found", detail={"requested_name": name}
            )

        # try default model
        config_dict = await self.storage.get_embedding_model("default")
        if config_dict:
            return EmbeddingModelConfig(**config_dict)

        # try first model
        all_models = await self.storage.list_embedding_models()
        if all_models:
            return EmbeddingModelConfig(**all_models[0])

        raise LLMConfigNotFoundError(
            "no embedding models configured", detail={"checked": ["database"]}
        )

    async def list_embedding_models(self) -> list[EmbeddingModelConfig]:
        """list all configured embedding models"""
        models_dict = await self.storage.list_embedding_models()
        return [EmbeddingModelConfig(**m) for m in models_dict]

    async def save_embedding_model(self, config: EmbeddingModelConfig) -> None:
        """create or update embedding model config"""
        await self.storage.save_embedding_model(config.model_dump())

    async def delete_embedding_model(self, name: str) -> None:
        """delete embedding model config"""
        success = await self.storage.delete_embedding_model(name)
        if not success:
            raise LLMConfigNotFoundError(
                f"embedding model '{name}' not found", detail={"name": name}
            )

    async def test_embedding_connection(self, config: EmbeddingModelConfig) -> ConnectionTestResult:
        """test embedding connection with simple text

        - sends "test" embedding request
        - 10 second timeout
        - returns success, message, latency_ms
        """
        start_time = time.time()
        try:
            # test embedding call using litellm
            embedding_params = self._prepare_embedding_call(config, input_text="test")
            await litellm.aembedding(**embedding_params)
            latency_ms = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=True, message="connection successful", latency_ms=latency_ms
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return ConnectionTestResult(
                success=False, message=f"connection failed: {str(e)}", latency_ms=latency_ms
            )

    def prepare_llm_call(self, config: LLMModelConfig, **litellm_params: Any) -> dict[str, Any]:
        """convert config to litellm parameters based on provider

        ollama needs special handling because litellm expects "ollama/" prefix
        and requires base url extraction from full endpoint
        """
        params = litellm_params.copy()

        if config.provider == LLMProvider.OLLAMA:
            # add ollama/ prefix to model name
            params["model"] = f"ollama/{config.model_name}"
            # extract base url from endpoint (remove /v1/chat/completions or similar)
            base_url = re.sub(r"/v1/.*$", "", config.endpoint)
            params["api_base"] = base_url
            # ollama doesn't need api_key
        else:
            params["model"] = config.model_name
            params["api_base"] = config.endpoint
            if config.api_key:
                params["api_key"] = config.api_key

        return params

    def _prepare_embedding_call(
        self, config: EmbeddingModelConfig, input_text: str
    ) -> dict[str, Any]:
        """convert embedding config to litellm parameters

        uses same provider-specific logic as prepare_llm_call
        """
        params = {"input": input_text}

        if config.provider == LLMProvider.OLLAMA:
            params["model"] = f"ollama/{config.model_name}"
            base_url = re.sub(r"/v1/.*$", "", config.endpoint)
            params["api_base"] = base_url
        else:
            params["model"] = config.model_name
            params["api_base"] = config.endpoint
            if config.api_key:
                params["api_key"] = config.api_key

        return params

    def _detect_provider_from_endpoint(self, endpoint: str) -> LLMProvider:
        """detect provider from endpoint url"""
        endpoint_lower = endpoint.lower()
        if "11434" in endpoint_lower or "ollama" in endpoint_lower:
            return LLMProvider.OLLAMA
        if "anthropic" in endpoint_lower:
            return LLMProvider.ANTHROPIC
        if "generativelanguage" in endpoint_lower or "gemini" in endpoint_lower:
            return LLMProvider.GEMINI
        # default to openai for unknown endpoints
        return LLMProvider.OPENAI
