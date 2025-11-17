import pytest
import pytest_asyncio

from lib.llm_config import LLMConfigManager, LLMConfigNotFoundError
from lib.storage import Storage
from models import EmbeddingModelConfig, LLMModelConfig, LLMProvider


@pytest_asyncio.fixture
async def storage():
    """create in-memory storage for testing"""
    storage = Storage(":memory:")
    await storage.init_db()
    yield storage
    await storage.close()


@pytest_asyncio.fixture
async def llm_config_manager(storage):
    """create llm config manager with test storage"""
    return LLMConfigManager(storage)


@pytest.mark.asyncio
async def test_save_and_get_llm_model(llm_config_manager):
    """test saving and retrieving llm model"""
    config = LLMModelConfig(
        name="test-model",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key="test-key",
        model_name="gpt-4",
    )

    await llm_config_manager.save_llm_model(config)
    retrieved = await llm_config_manager.get_llm_model("test-model")

    assert retrieved.name == "test-model"
    assert retrieved.provider == LLMProvider.OPENAI
    assert retrieved.endpoint == "https://api.openai.com/v1/chat/completions"
    assert retrieved.api_key == "test-key"
    assert retrieved.model_name == "gpt-4"


@pytest.mark.asyncio
async def test_list_llm_models(llm_config_manager):
    """test listing all llm models"""
    config1 = LLMModelConfig(
        name="model1",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key="key1",
        model_name="gpt-4",
    )
    config2 = LLMModelConfig(
        name="model2",
        provider=LLMProvider.ANTHROPIC,
        endpoint="https://api.anthropic.com/v1/messages",
        api_key="key2",
        model_name="claude-3-opus",
    )

    await llm_config_manager.save_llm_model(config1)
    await llm_config_manager.save_llm_model(config2)

    models = await llm_config_manager.list_llm_models()
    # may have default model from .env migration
    assert len(models) >= 2
    model_names = {m.name for m in models}
    assert "model1" in model_names
    assert "model2" in model_names


@pytest.mark.asyncio
async def test_update_llm_model(llm_config_manager):
    """test updating existing llm model"""
    config = LLMModelConfig(
        name="test-model",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key="old-key",
        model_name="gpt-4",
    )

    await llm_config_manager.save_llm_model(config)

    # update with new api key
    updated_config = LLMModelConfig(
        name="test-model",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key="new-key",
        model_name="gpt-4-turbo",
    )

    await llm_config_manager.save_llm_model(updated_config)
    retrieved = await llm_config_manager.get_llm_model("test-model")

    assert retrieved.api_key == "new-key"
    assert retrieved.model_name == "gpt-4-turbo"


@pytest.mark.asyncio
async def test_delete_llm_model(llm_config_manager):
    """test deleting llm model"""
    config = LLMModelConfig(
        name="test-model",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key="test-key",
        model_name="gpt-4",
    )

    await llm_config_manager.save_llm_model(config)
    await llm_config_manager.delete_llm_model("test-model")

    with pytest.raises(LLMConfigNotFoundError):
        await llm_config_manager.get_llm_model("test-model")


@pytest.mark.asyncio
async def test_get_llm_model_not_found(llm_config_manager):
    """test getting non-existent model raises error"""
    with pytest.raises(LLMConfigNotFoundError):
        await llm_config_manager.get_llm_model("non-existent")


@pytest.mark.asyncio
async def test_get_llm_model_default_fallback(llm_config_manager):
    """test fallback to default model"""
    default_config = LLMModelConfig(
        name="default",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key="test-key",
        model_name="gpt-4",
    )

    await llm_config_manager.save_llm_model(default_config)
    retrieved = await llm_config_manager.get_llm_model(None)

    assert retrieved.name == "default"


@pytest.mark.asyncio
async def test_get_llm_model_first_fallback(llm_config_manager):
    """test fallback to first model when no default"""
    # if default exists from .env migration, use it; otherwise test first-model fallback
    models = await llm_config_manager.list_llm_models()
    has_default = any(m.name == "default" for m in models)

    config = LLMModelConfig(
        name="first-model",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key="test-key",
        model_name="gpt-4",
    )

    await llm_config_manager.save_llm_model(config)
    retrieved = await llm_config_manager.get_llm_model(None)

    # should fallback to default if exists, otherwise first-model
    if has_default:
        assert retrieved.name == "default"
    else:
        assert retrieved.name == "first-model"


@pytest.mark.asyncio
async def test_prepare_llm_call_openai(llm_config_manager):
    """test preparing litellm call for openai"""
    config = LLMModelConfig(
        name="test",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key="test-key",
        model_name="gpt-4",
    )

    params = llm_config_manager.prepare_llm_call(
        config, messages=[{"role": "user", "content": "hello"}], temperature=0.7
    )

    assert params["model"] == "gpt-4"
    assert params["api_base"] == "https://api.openai.com/v1/chat/completions"
    assert params["api_key"] == "test-key"
    assert params["temperature"] == 0.7


@pytest.mark.asyncio
async def test_prepare_llm_call_ollama(llm_config_manager):
    """test preparing litellm call for ollama"""
    config = LLMModelConfig(
        name="test",
        provider=LLMProvider.OLLAMA,
        endpoint="http://localhost:11434/v1/chat/completions",
        api_key=None,
        model_name="llama3",
    )

    params = llm_config_manager.prepare_llm_call(
        config, messages=[{"role": "user", "content": "hello"}]
    )

    assert params["model"] == "ollama/llama3"
    assert params["api_base"] == "http://localhost:11434"
    assert "api_key" not in params or params["api_key"] is None


@pytest.mark.asyncio
async def test_prepare_llm_call_anthropic(llm_config_manager):
    """test preparing litellm call for anthropic"""
    config = LLMModelConfig(
        name="test",
        provider=LLMProvider.ANTHROPIC,
        endpoint="https://api.anthropic.com/v1/messages",
        api_key="test-key",
        model_name="claude-3-opus-20240229",
    )

    params = llm_config_manager.prepare_llm_call(config, messages=[])

    assert params["model"] == "anthropic/claude-3-opus-20240229"
    assert params["api_base"] == "https://api.anthropic.com/v1/messages"
    assert params["api_key"] == "test-key"


@pytest.mark.asyncio
async def test_save_and_get_embedding_model(llm_config_manager):
    """test saving and retrieving embedding model"""
    config = EmbeddingModelConfig(
        name="test-embedding",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/embeddings",
        api_key="test-key",
        model_name="text-embedding-ada-002",
        dimensions=1536,
    )

    await llm_config_manager.save_embedding_model(config)
    retrieved = await llm_config_manager.get_embedding_model("test-embedding")

    assert retrieved.name == "test-embedding"
    assert retrieved.provider == LLMProvider.OPENAI
    assert retrieved.model_name == "text-embedding-ada-002"
    assert retrieved.dimensions == 1536


@pytest.mark.asyncio
async def test_list_embedding_models(llm_config_manager):
    """test listing all embedding models"""
    config1 = EmbeddingModelConfig(
        name="embedding1",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/embeddings",
        api_key="key1",
        model_name="text-embedding-ada-002",
        dimensions=1536,
    )
    config2 = EmbeddingModelConfig(
        name="embedding2",
        provider=LLMProvider.OLLAMA,
        endpoint="http://localhost:11434/v1/embeddings",
        api_key=None,
        model_name="nomic-embed-text",
        dimensions=768,
    )

    await llm_config_manager.save_embedding_model(config1)
    await llm_config_manager.save_embedding_model(config2)

    models = await llm_config_manager.list_embedding_models()
    assert len(models) == 2


@pytest.mark.asyncio
async def test_delete_embedding_model(llm_config_manager):
    """test deleting embedding model"""
    config = EmbeddingModelConfig(
        name="test-embedding",
        provider=LLMProvider.OPENAI,
        endpoint="https://api.openai.com/v1/embeddings",
        api_key="test-key",
        model_name="text-embedding-ada-002",
        dimensions=1536,
    )

    await llm_config_manager.save_embedding_model(config)
    await llm_config_manager.delete_embedding_model("test-embedding")

    with pytest.raises(LLMConfigNotFoundError):
        await llm_config_manager.get_embedding_model("test-embedding")


@pytest.mark.asyncio
async def test_provider_detection_ollama(llm_config_manager):
    """test provider detection from endpoint for ollama"""
    endpoint = "http://localhost:11434/v1/chat/completions"
    provider = llm_config_manager._detect_provider_from_endpoint(endpoint)
    assert provider == LLMProvider.OLLAMA


@pytest.mark.asyncio
async def test_provider_detection_anthropic(llm_config_manager):
    """test provider detection from endpoint for anthropic"""
    endpoint = "https://api.anthropic.com/v1/messages"
    provider = llm_config_manager._detect_provider_from_endpoint(endpoint)
    assert provider == LLMProvider.ANTHROPIC


@pytest.mark.asyncio
async def test_provider_detection_gemini(llm_config_manager):
    """test provider detection from endpoint for gemini"""
    endpoint = "https://generativelanguage.googleapis.com/v1/models"
    provider = llm_config_manager._detect_provider_from_endpoint(endpoint)
    assert provider == LLMProvider.GEMINI


@pytest.mark.asyncio
async def test_provider_detection_default_openai(llm_config_manager):
    """test provider detection defaults to openai"""
    endpoint = "https://custom-api.example.com/v1/chat"
    provider = llm_config_manager._detect_provider_from_endpoint(endpoint)
    assert provider == LLMProvider.OPENAI
