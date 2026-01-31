"""
Registry regression tests — lock current BlockRegistry behavior before extensibility changes.
"""
from lib.blocks.base import BaseBlock
from lib.blocks.registry import BlockRegistry
from lib.entities.extensions import BlockInfo


def test_registry_discovers_all_builtin_blocks():
    reg = BlockRegistry()
    block_types = {b.type for b in reg.list_blocks()}

    expected = {
        "TextGenerator",
        "StructuredGenerator",
        "ValidatorBlock",
        "JSONValidatorBlock",
        "FieldMapper",
        "DiversityScore",
        "CoherenceScore",
        "RougeScore",
        "RagasMetrics",
        "MarkdownMultiplierBlock",
        "DuplicateRemover",
        "LangfuseDatasetBlock",
        "StructureSampler",
        "SemanticInfiller",
    }
    assert expected.issubset(block_types), f"Missing blocks: {expected - block_types}"


def test_registry_get_block_class_returns_class():
    reg = BlockRegistry()
    cls = reg.get_block_class("TextGenerator")
    assert cls is not None
    assert issubclass(cls, BaseBlock)


def test_registry_get_block_class_returns_none_for_unknown():
    reg = BlockRegistry()
    assert reg.get_block_class("DoesNotExist") is None


def test_registry_list_blocks_returns_block_info():
    reg = BlockRegistry()
    blocks = reg.list_blocks()
    assert isinstance(blocks, list)
    for block in blocks:
        assert isinstance(block, BlockInfo)
        assert block.type
        assert block.name
        assert block.category
        assert isinstance(block.inputs, list)
        assert isinstance(block.outputs, list)
        assert isinstance(block.config_schema, dict)


def test_registry_compute_accumulated_state_schema():
    reg = BlockRegistry()
    blocks = [
        {"type": "TextGenerator", "config": {}},
        {"type": "ValidatorBlock", "config": {}},
    ]
    fields = reg.compute_accumulated_state_schema(blocks)
    assert isinstance(fields, list)
    assert fields == sorted(fields), "fields should be sorted"


def test_registry_skips_base_classes():
    """BaseBlock and BaseMultiplierBlock should not be registered"""
    reg = BlockRegistry()
    block_types = {b.type for b in reg.list_blocks()}
    assert "BaseBlock" not in block_types
    assert "BaseMultiplierBlock" not in block_types


def test_registry_multiplier_block_detected():
    reg = BlockRegistry()
    cls = reg.get_block_class("MarkdownMultiplierBlock")
    assert cls is not None
    assert getattr(cls, "is_multiplier", False) is True
