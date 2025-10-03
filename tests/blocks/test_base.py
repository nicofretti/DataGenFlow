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

    assert "param1" in schema["config_schema"]
    assert schema["config_schema"]["param1"]["type"] == "string"
    assert schema["config_schema"]["param1"]["required"] is True

    assert "param2" in schema["config_schema"]
    assert schema["config_schema"]["param2"]["type"] == "number"
    assert schema["config_schema"]["param2"]["required"] is False
    assert schema["config_schema"]["param2"]["default"] == 10


@pytest.mark.asyncio
async def test_execute():
    block = DummyBlock(param1="test", param2=20)
    result = await block.execute({"input1": "dummy"})

    assert result["output1"] == "test:20"
