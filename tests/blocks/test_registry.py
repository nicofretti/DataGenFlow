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


class TestBlockRegistryReload:
    """tests for registry reload functionality"""

    def test_reload_method_exists(self):
        """registry has reload method"""
        registry = BlockRegistry()
        assert hasattr(registry, "reload")
        assert callable(registry.reload)

    def test_reload_preserves_block_count(self):
        """reload discovers same blocks"""
        registry = BlockRegistry()
        initial_count = len(registry.list_blocks())

        registry.reload()

        assert len(registry.list_blocks()) == initial_count

    def test_reload_preserves_builtin_blocks(self):
        """reload keeps builtin blocks available"""
        registry = BlockRegistry()
        before = {b.type for b in registry.list_blocks() if b.source == "builtin"}

        registry.reload()

        after = {b.type for b in registry.list_blocks() if b.source == "builtin"}
        assert before == after


class TestBlockRegistryGetEntry:
    """tests for get_entry method"""

    def test_get_entry_returns_block_entry(self):
        """get_entry returns BlockEntry for known block"""
        registry = BlockRegistry()
        entry = registry.get_entry("TextGenerator")

        assert entry is not None
        assert entry.available is True
        assert entry.source == "builtin"
        assert entry.block_class.__name__ == "TextGenerator"

    def test_get_entry_returns_none_for_unknown(self):
        """get_entry returns None for unknown block"""
        registry = BlockRegistry()
        entry = registry.get_entry("NonExistentBlock")

        assert entry is None

    def test_get_entry_has_block_class(self):
        """entry contains valid block class"""
        registry = BlockRegistry()
        entry = registry.get_entry("ValidatorBlock")

        assert entry is not None
        assert hasattr(entry.block_class, "execute")
        assert hasattr(entry.block_class, "inputs")
        assert hasattr(entry.block_class, "outputs")
