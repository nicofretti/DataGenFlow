"""
Tests for enhanced BlockRegistry: source tracking, register/unregister, unavailable blocks.
"""
from lib.blocks.base import BaseBlock
from lib.blocks.registry import BlockRegistry
from lib.entities.extensions import BlockInfo


class FakeUserBlock(BaseBlock):
    name = "Fake User Block"
    description = "A user-provided block"
    category = "validators"
    inputs = ["text"]
    outputs = ["result"]

    async def execute(self, context):
        return {"result": "ok"}


class BlockWithDeps(BaseBlock):
    name = "Block With Deps"
    description = "Needs missing deps"
    category = "generators"
    inputs = ["text"]
    outputs = ["result"]
    dependencies = ["some_nonexistent_package>=1.0.0"]

    async def execute(self, context):
        return {"result": "ok"}


# --- source tracking ---


def test_list_blocks_includes_source_field():
    reg = BlockRegistry()
    blocks = reg.list_blocks()
    for block in blocks:
        assert isinstance(block, BlockInfo)
        assert block.source is not None


def test_builtin_blocks_have_builtin_source():
    reg = BlockRegistry()
    blocks = reg.list_blocks()
    text_gen = next(b for b in blocks if b.type == "TextGenerator")
    assert text_gen.source == "builtin"


def test_list_blocks_includes_available_field():
    reg = BlockRegistry()
    blocks = reg.list_blocks()
    for block in blocks:
        assert isinstance(block.available, bool)


def test_builtin_blocks_are_available():
    reg = BlockRegistry()
    blocks = reg.list_blocks()
    text_gen = next(b for b in blocks if b.type == "TextGenerator")
    assert text_gen.available is True


# --- register / unregister ---


def test_register_user_block():
    reg = BlockRegistry()
    initial_count = len(reg.list_blocks())
    reg.register(FakeUserBlock, source="user")
    blocks = reg.list_blocks()
    assert len(blocks) == initial_count + 1
    fake = next(b for b in blocks if b.type == "FakeUserBlock")
    assert fake.source == "user"
    assert fake.available is True


def test_unregister_block():
    reg = BlockRegistry()
    reg.register(FakeUserBlock, source="user")
    assert reg.get_block_class("FakeUserBlock") is not None

    reg.unregister("FakeUserBlock")
    assert reg.get_block_class("FakeUserBlock") is None


def test_unregister_nonexistent_is_noop():
    reg = BlockRegistry()
    reg.unregister("DoesNotExist")  # should not raise


def test_register_replaces_existing():
    reg = BlockRegistry()
    reg.register(FakeUserBlock, source="user")
    reg.register(FakeUserBlock, source="user")
    matches = [b for b in reg.list_blocks() if b.type == "FakeUserBlock"]
    assert len(matches) == 1


# --- unavailable blocks ---


def test_register_unavailable_block():
    reg = BlockRegistry()
    reg.register(BlockWithDeps, source="user", available=False, error="Missing: some_nonexistent_package")
    blocks = reg.list_blocks()
    block = next(b for b in blocks if b.type == "BlockWithDeps")
    assert block.available is False
    assert block.error is not None
    assert "some_nonexistent_package" in block.error


def test_unavailable_block_class_still_accessible():
    """even unavailable blocks can be retrieved by class for inspection"""
    reg = BlockRegistry()
    reg.register(BlockWithDeps, source="user", available=False, error="missing deps")
    cls = reg.get_block_class("BlockWithDeps")
    assert cls is not None
    assert cls is BlockWithDeps


# --- get_block_source ---


def test_get_block_source():
    reg = BlockRegistry()
    reg.register(FakeUserBlock, source="user")
    assert reg.get_block_source("FakeUserBlock") == "user"
    assert reg.get_block_source("TextGenerator") == "builtin"
    assert reg.get_block_source("NonExistent") is None
