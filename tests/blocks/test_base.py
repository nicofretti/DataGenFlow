import pytest

from lib.blocks.base import BaseBlock


class DummyBlock(BaseBlock):
    name = "Dummy Block"
    description = "Test block"
    inputs = ["input1"]
    outputs = ["output1"]

    def __init__(self, param1: str, param2: int = 10):
        self.param1 = param1
        self.param2 = param2

    async def execute(self, data):
        return {"output1": f"{self.param1}:{self.param2}"}


def test_get_schema():
    schema = DummyBlock.get_schema()

    assert schema["type"] == "DummyBlock"
    assert schema["name"] == "Dummy Block"
    assert schema["description"] == "Test block"
    assert schema["inputs"] == ["input1"]
    assert schema["outputs"] == ["output1"]

    # check JSON schema format
    config_schema = schema["config_schema"]
    assert config_schema["type"] == "object"
    assert "param1" in config_schema["properties"]
    assert config_schema["properties"]["param1"]["type"] == "string"
    assert "param1" in config_schema["required"]

    assert "param2" in config_schema["properties"]
    assert config_schema["properties"]["param2"]["type"] == "integer"
    assert "param2" not in config_schema["required"]
    assert config_schema["properties"]["param2"]["default"] == 10


@pytest.mark.asyncio
async def test_execute():
    block = DummyBlock(param1="test", param2=20)
    result = await block.execute({"input1": "dummy"})

    assert result["output1"] == "test:20"
