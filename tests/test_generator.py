import pytest
from lib.generator import Generator
from models import GenerationConfig


@pytest.mark.asyncio
async def test_generation():
    """Test generator with config"""
    config = GenerationConfig(model="test-model")
    gen = Generator(config)

    assert gen.config.model == "test-model"
    # actual generation test would require mocking or live endpoint
