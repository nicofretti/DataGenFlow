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

    def _validate_output(self, block: Any, result: dict[str, Any]) -> None:
        # validate block returns only declared outputs
        declared = set(block.outputs)
        actual = set(result.keys())
        if not actual.issubset(declared):
            extra = actual - declared
            raise ValueError(
                f"{block.__class__.__name__} returned undeclared fields: {extra}. "
                f"Declared outputs: {declared}, Actual: {actual}"
            )

    async def execute(self, initial_data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        accumulated_data = initial_data.copy()
        trace = []

        for i, block in enumerate(self._block_instances):
            try:
                block_input = accumulated_data.copy()
                result = await block.execute(accumulated_data)

                # validate output matches declared schema
                self._validate_output(block, result)

                # merge result into accumulated data
                accumulated_data.update(result)

                # set pipeline_output if not already set and this is the last block
                is_last_block = i == len(self._block_instances) - 1
                if is_last_block and "pipeline_output" not in accumulated_data:
                    if "assistant" in accumulated_data:
                        accumulated_data["pipeline_output"] = accumulated_data["assistant"]
                    elif block.outputs:
                        # use this block's first output
                        first_output = block.outputs[0]
                        accumulated_data["pipeline_output"] = accumulated_data.get(first_output, "")
                    else:
                        accumulated_data["pipeline_output"] = ""

                # capture trace with accumulated state (after pipeline_output is set)
                trace.append({
                    "block_type": block.__class__.__name__,
                    "input": block_input,
                    "output": result,
                    "accumulated_state": accumulated_data.copy(),
                })
            except Exception as e:
                raise RuntimeError(f"block {i} ({block.__class__.__name__}) failed: {e}")

        return accumulated_data, trace

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "blocks": self.blocks}
