"""Test fixtures for e2e tests with real LLM/embedding models"""

import os

import pytest_asyncio

from lib.entities import EmbeddingModelConfig, LLMModelConfig, LLMProvider
from lib.storage import Storage

# configurable ollama endpoint for different environments
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")


@pytest_asyncio.fixture
async def e2e_storage():
    """create test database with real LLM and embedding model configs"""
    os.makedirs("data", exist_ok=True)

    storage = Storage("data/test_e2e_records.db")
    await storage.init_db()

    # add default LLM model (ollama gemma3:1b)
    llm_config = LLMModelConfig(
        name="default",
        provider=LLMProvider.OLLAMA,
        endpoint=f"{OLLAMA_ENDPOINT}/v1/chat/completions",
        api_key="",
        model_name="gemma3:1b",
    )
    await storage.save_llm_model(llm_config)

    # add ollama-nomic embedding model
    embedding_config = EmbeddingModelConfig(
        name="ollama-nomic",
        provider=LLMProvider.OLLAMA,
        endpoint=f"{OLLAMA_ENDPOINT}/v1/embeddings",
        api_key="",
        model_name="nomic-embed-text",
        dimensions=768,
    )
    await storage.save_embedding_model(embedding_config)

    yield storage

    # cleanup
    try:
        await storage.close()
    finally:
        # clean up database and WAL files
        db_path = "data/test_e2e_records.db"
        for suffix in ("", "-wal", "-shm"):
            path = db_path + suffix
            if os.path.exists(path):
                os.remove(path)
