from lib.blocks.registry import BlockRegistry


def test_registry_discovers_blocks():
    registry = BlockRegistry()

    blocks = registry.list_blocks()

    # should discover at least the core blocks
    block_types = [b.type for b in blocks]
    assert "TextGenerator" in block_types
    assert "ValidatorBlock" in block_types
    assert "JSONValidatorBlock" in block_types


def test_get_block_class():
    registry = BlockRegistry()

    llm_class = registry.get_block_class("TextGenerator")
    assert llm_class is not None
    assert llm_class.__name__ == "TextGenerator"

    invalid_class = registry.get_block_class("NonExistent")
    assert invalid_class is None
