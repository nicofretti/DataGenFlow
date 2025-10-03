from typing import Any

from lib.blocks.registry import registry


class Pipeline:
    def __init__(self, name: str, blocks: list[dict[str, Any]]) -> None:
        self.name = name
        self.blocks = blocks
        self._block_instances: list[Any] = []
        self._initialize_blocks()

    def _initialize_blocks(self) -> None:
        for block_def in self.blocks:
            block_type = block_def["type"]
            block_config = block_def.get("config", {})

            block_class = registry.get_block_class(block_type)
            if not block_class:
                raise ValueError(f"unknown block type: {block_type}")

            self._block_instances.append(block_class(**block_config))

    @classmethod
    def load_from_dict(cls, data: dict[str, Any]) -> "Pipeline":
        return cls(name=data["name"], blocks=data["blocks"])

    async def execute(self, initial_data: dict[str, Any]) -> dict[str, Any]:
        data = initial_data.copy()

        for i, block in enumerate(self._block_instances):
            try:
                result = await block.execute(data)
                # merge result into data for next block
                data.update(result)
            except Exception as e:
                raise RuntimeError(f"block {i} ({block.__class__.__name__}) failed: {e}")

        return data

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "blocks": self.blocks}
