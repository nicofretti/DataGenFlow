"""
Tests for dependency manager: parse, check, info.
"""
from lib.blocks.base import BaseBlock


class BlockWithDeps(BaseBlock):
    name = "Test"
    description = "Test"
    category = "general"
    inputs = []
    outputs = []
    dependencies = ["requests>=2.28.0", "pandas>=1.5.0"]

    async def execute(self, context):
        return {}


class BlockNoDeps(BaseBlock):
    name = "No Deps"
    description = "No deps"
    category = "general"
    inputs = []
    outputs = []

    async def execute(self, context):
        return {}


def test_get_block_dependencies():
    from lib.dependency_manager import DependencyManager

    manager = DependencyManager()
    assert manager.get_block_dependencies(BlockWithDeps) == [
        "requests>=2.28.0",
        "pandas>=1.5.0",
    ]


def test_get_block_dependencies_empty():
    from lib.dependency_manager import DependencyManager

    manager = DependencyManager()
    assert manager.get_block_dependencies(BlockNoDeps) == []


def test_check_missing_returns_uninstalled():
    from lib.dependency_manager import DependencyManager

    manager = DependencyManager()
    missing = manager.check_missing(["nonexistent-package-xyz123"])
    assert "nonexistent-package-xyz123" in missing


def test_check_missing_returns_empty_for_installed():
    from lib.dependency_manager import DependencyManager

    manager = DependencyManager()
    missing = manager.check_missing(["pytest"])
    assert missing == []


def test_check_missing_handles_version_specifiers():
    from lib.dependency_manager import DependencyManager

    manager = DependencyManager()
    # pytest is installed, version spec shouldn't break parsing
    missing = manager.check_missing(["pytest>=1.0.0"])
    assert missing == []


def test_get_dependency_info_installed():
    from lib.dependency_manager import DependencyManager

    manager = DependencyManager()
    info = manager.get_dependency_info(["pytest"])
    assert len(info) == 1
    assert info[0].name == "pytest"
    assert info[0].status == "ok"
    assert info[0].installed_version is not None


def test_get_dependency_info_not_installed():
    from lib.dependency_manager import DependencyManager

    manager = DependencyManager()
    info = manager.get_dependency_info(["nonexistent-xyz-999"])
    assert len(info) == 1
    assert info[0].status == "not_installed"
    assert info[0].installed_version is None


def test_get_dependency_info_mixed():
    from lib.dependency_manager import DependencyManager

    manager = DependencyManager()
    info = manager.get_dependency_info(["pytest", "nonexistent-xyz-999"])
    assert len(info) == 2

    by_name = {i.name: i for i in info}
    assert by_name["pytest"].status == "ok"
    assert by_name["nonexistent-xyz-999"].status == "not_installed"
