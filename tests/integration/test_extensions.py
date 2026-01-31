"""
Integration tests for the extensions system.
Tests the full stack: registry + API + dependency manager working together.
"""


class TestExtensionsFullStack:
    """tests that exercise registry -> API -> response chain"""

    def test_extensions_status_counts_match_blocks_list(self, client):
        """status endpoint counts should match actual blocks list length"""
        status = client.get("/api/extensions/status").json()
        blocks = client.get("/api/extensions/blocks").json()

        assert status["blocks"]["total"] == len(blocks)
        assert status["blocks"]["available"] == sum(1 for b in blocks if b["available"])
        assert status["blocks"]["unavailable"] == sum(1 for b in blocks if not b["available"])

    def test_extensions_status_counts_match_templates_list(self, client):
        """status template counts should match actual templates list length"""
        status = client.get("/api/extensions/status").json()
        templates = client.get("/api/extensions/templates").json()

        assert status["templates"]["total"] == len(templates)

    def test_all_blocks_have_extensibility_fields(self, client):
        """every block from extensions endpoint has source and available fields"""
        blocks = client.get("/api/extensions/blocks").json()
        assert len(blocks) > 0

        for block in blocks:
            assert "source" in block
            assert "available" in block
            assert "dependencies" in block
            assert block["source"] in ("builtin", "custom", "user")

    def test_all_templates_have_source(self, client):
        """every template from extensions endpoint has source field"""
        templates = client.get("/api/extensions/templates").json()
        assert len(templates) > 0

        for tmpl in templates:
            assert "source" in tmpl
            assert tmpl["source"] in ("builtin", "user")

    def test_validate_then_check_dependencies(self, client):
        """validate a block, then check its dependencies - full flow"""
        resp = client.post("/api/extensions/blocks/TextGenerator/validate")
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

        resp = client.get("/api/extensions/blocks/TextGenerator/dependencies")
        assert resp.status_code == 200
        deps = resp.json()
        assert isinstance(deps, list)

    def test_reload_preserves_builtin_blocks(self, client):
        """reloading extensions should not lose builtin blocks"""
        blocks_before = client.get("/api/extensions/blocks").json()
        builtin_before = [b["type"] for b in blocks_before if b["source"] == "builtin"]

        client.post("/api/extensions/reload")

        blocks_after = client.get("/api/extensions/blocks").json()
        builtin_after = [b["type"] for b in blocks_after if b["source"] == "builtin"]

        assert set(builtin_before) == set(builtin_after)

    def test_validate_nonexistent_block_returns_404(self, client):
        resp = client.post("/api/extensions/blocks/DoesNotExist/validate")
        assert resp.status_code == 404

    def test_dependencies_nonexistent_block_returns_404(self, client):
        resp = client.get("/api/extensions/blocks/DoesNotExist/dependencies")
        assert resp.status_code == 404

    def test_install_deps_nonexistent_block_returns_404(self, client):
        resp = client.post("/api/extensions/blocks/DoesNotExist/install-deps")
        assert resp.status_code == 404


class TestRegistryWithUserBlocks:
    """tests for dynamic block registration via the registry"""

    def test_register_and_list_user_block(self):
        """registering a block makes it appear in list_blocks"""
        from lib.blocks.base import BaseBlock
        from lib.blocks.registry import BlockRegistry

        registry = BlockRegistry()
        initial_count = len(registry.list_blocks())

        class DummyIntegrationBlock(BaseBlock):
            name = "Dummy Integration"
            description = "test block"
            category = "generators"
            inputs = ["text"]
            outputs = ["result"]

        registry.register(DummyIntegrationBlock, source="user")

        blocks = registry.list_blocks()
        assert len(blocks) == initial_count + 1

        dummy = next(b for b in blocks if b.type == "DummyIntegrationBlock")
        assert dummy.source == "user"
        assert dummy.available is True

        registry.unregister("DummyIntegrationBlock")
        assert len(registry.list_blocks()) == initial_count

    def test_register_unavailable_block(self):
        """registering an unavailable block shows error info"""
        from lib.blocks.base import BaseBlock
        from lib.blocks.registry import BlockRegistry

        registry = BlockRegistry()

        class BrokenIntegrationBlock(BaseBlock):
            name = "Broken"
            description = "broken block"
            category = "generators"
            inputs = ["text"]
            outputs = ["result"]
            dependencies = ["nonexistent-package-xyz"]

        registry.register(
            BrokenIntegrationBlock,
            source="user",
            available=False,
            error="missing dependency: nonexistent-package-xyz",
        )

        blocks = registry.list_blocks()
        broken = next(b for b in blocks if b.type == "BrokenIntegrationBlock")
        assert broken.available is False
        assert "nonexistent-package-xyz" in broken.error

        registry.unregister("BrokenIntegrationBlock")


class TestDependencyManagerIntegration:
    """tests for dependency checking with real packages"""

    def test_check_installed_package(self):
        """pydantic should be detected as installed"""
        from lib.dependency_manager import dependency_manager

        missing = dependency_manager.check_missing(["pydantic"])
        assert "pydantic" not in missing

    def test_check_missing_package(self):
        """nonexistent package should be detected as missing"""
        from lib.dependency_manager import dependency_manager

        missing = dependency_manager.check_missing(["nonexistent-package-xyz-999"])
        assert "nonexistent-package-xyz-999" in missing

    def test_get_dependency_info_installed(self):
        """dependency info for installed package has version"""
        from lib.dependency_manager import dependency_manager

        info = dependency_manager.get_dependency_info(["pydantic"])
        assert len(info) == 1
        assert info[0].status == "ok"
        assert info[0].installed_version is not None

    def test_get_dependency_info_missing(self):
        """dependency info for missing package shows not_installed"""
        from lib.dependency_manager import dependency_manager

        info = dependency_manager.get_dependency_info(["nonexistent-package-xyz-999"])
        assert len(info) == 1
        assert info[0].status == "not_installed"
        assert info[0].installed_version is None
