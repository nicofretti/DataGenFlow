import pytest
from lib.blocks.base import BaseBlock


class TestBlockConfig(BaseBlock):
    name = "Test Block"
    description = "For testing"
    inputs = []
    outputs = ["result"]

    def __init__(self, param1: str = "default", param2: int = 42):
        self.param1 = param1
        self.param2 = param2

    async def execute(self, data: dict):
        return {"result": f"{self.param1}_{self.param2}"}


def test_block_has_config_schema():
    schema = TestBlockConfig.get_config_schema()
    assert "param1" in schema["properties"]
    assert "param2" in schema["properties"]
    assert schema["properties"]["param1"]["type"] == "string"
    assert schema["properties"]["param2"]["type"] == "integer"
    assert schema["properties"]["param1"]["default"] == "default"


def test_block_config_separate_from_runtime():
    # config is set at pipeline build time
    block = TestBlockConfig(param1="custom", param2=100)
    assert block.param1 == "custom"
    assert block.param2 == 100
