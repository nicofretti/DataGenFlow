from typing import Any

from lib.blocks.registry import registry


def compute_accumulated_state_schema(blocks: list[dict[str, Any]]) -> list[str]:
    """
    returns list of field names that will be in accumulated state
    by examining block outputs from registry
    """
    fields = set()

    for block_def in blocks:
        block_type = block_def["type"]
        block_class = registry.get_block_class(block_type)

        if block_class and hasattr(block_class, "outputs"):
            fields.update(block_class.outputs)

    return sorted(list(fields))
