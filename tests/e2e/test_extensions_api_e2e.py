"""
E2E tests for extensions REST API.
Tests the backend API endpoints directly via HTTP,
complementing the Playwright UI tests.

Requires: running server (uvicorn on port 8000).
"""

import pytest

try:
    from .test_helpers import (
        cleanup_database,
        get_block_dependencies,
        get_blocks_list,
        get_extensions_status,
        get_templates_list,
        reload_extensions,
        validate_block,
        wait_for_server,
    )
except ImportError:
    from test_helpers import (
        cleanup_database,
        get_block_dependencies,
        get_blocks_list,
        get_extensions_status,
        get_templates_list,
        reload_extensions,
        validate_block,
        wait_for_server,
    )

import httpx

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module", autouse=True)
def _e2e_setup():
    if not wait_for_server():
        pytest.skip("server not ready for e2e tests")
    cleanup_database()
    yield
    cleanup_database()


# --- GET /api/extensions/status ---


def test_status_returns_valid_structure():
    """verify status endpoint returns expected fields"""
    status = get_extensions_status()

    assert "blocks" in status
    assert "templates" in status

    blocks = status["blocks"]
    assert "total" in blocks
    assert "builtin_blocks" in blocks
    assert "custom_blocks" in blocks
    assert "user_blocks" in blocks
    assert "available" in blocks
    assert "unavailable" in blocks

    templates = status["templates"]
    assert "total" in templates
    assert "builtin_templates" in templates
    assert "user_templates" in templates


def test_status_counts_are_consistent():
    """verify status counts add up correctly"""
    status = get_extensions_status()

    blocks = status["blocks"]
    # total should equal sum of sources
    assert (
        blocks["total"]
        == blocks["builtin_blocks"] + blocks["custom_blocks"] + blocks["user_blocks"]
    )
    # total should equal available + unavailable
    assert blocks["total"] == blocks["available"] + blocks["unavailable"]
    # should have at least some builtin blocks
    assert blocks["builtin_blocks"] > 0


def test_status_block_count_matches_blocks_list():
    """verify status total matches actual blocks list length"""
    status = get_extensions_status()
    blocks = get_blocks_list()

    assert status["blocks"]["total"] == len(blocks)


def test_status_template_count_matches_templates_list():
    """verify status total matches actual templates list length"""
    status = get_extensions_status()
    templates = get_templates_list()

    assert status["templates"]["total"] == len(templates)


# --- GET /api/extensions/blocks ---


def test_blocks_list_returns_expected_fields():
    """verify each block has required fields"""
    blocks = get_blocks_list()
    assert len(blocks) > 0

    for block in blocks:
        assert "name" in block, f"block missing 'name': {block}"
        assert "type" in block, f"block missing 'type': {block}"
        assert "source" in block, f"block missing 'source': {block}"
        assert "available" in block, f"block missing 'available': {block}"
        assert "category" in block, f"block missing 'category': {block}"
        assert "dependencies" in block, f"block missing 'dependencies': {block}"
        assert isinstance(block["dependencies"], list)


def test_blocks_list_contains_known_builtin_blocks():
    """verify well-known builtin blocks are present"""
    blocks = get_blocks_list()
    block_types = {b["type"] for b in blocks}

    # these should always exist as builtin blocks
    expected_builtins = {"TextGenerator", "JSONValidatorBlock", "FieldMapper"}
    for expected in expected_builtins:
        assert expected in block_types, f"expected builtin block '{expected}' not found"


def test_blocks_list_contains_new_blocks():
    """verify new blocks from this branch are registered"""
    blocks = get_blocks_list()
    block_types = {b["type"] for b in blocks}

    new_blocks = {"DuplicateRemover", "SemanticInfiller", "StructureSampler"}
    for expected in new_blocks:
        assert expected in block_types, f"new block '{expected}' not found in registry"


def test_blocks_sources_are_valid():
    """verify all block sources are one of the allowed values"""
    blocks = get_blocks_list()
    valid_sources = {"builtin", "custom", "user"}

    for block in blocks:
        assert block["source"] in valid_sources, (
            f"block '{block['type']}' has invalid source '{block['source']}'"
        )


def test_blocks_categories_are_valid():
    """verify all block categories are known"""
    blocks = get_blocks_list()
    valid_categories = {
        "generators",
        "validators",
        "processors",
        "seeders",
        "metrics",
        "integrations",
        "utilities",
        "general",
    }

    for block in blocks:
        assert block["category"] in valid_categories, (
            f"block '{block['type']}' has unknown category '{block['category']}'"
        )


# --- GET /api/extensions/templates ---


def test_templates_list_returns_expected_fields():
    """verify each template has required fields"""
    templates = get_templates_list()
    assert len(templates) > 0

    for tmpl in templates:
        assert "id" in tmpl, f"template missing 'id': {tmpl}"
        assert "name" in tmpl, f"template missing 'name': {tmpl}"
        assert "source" in tmpl, f"template missing 'source': {tmpl}"
        assert "description" in tmpl, f"template missing 'description': {tmpl}"


def test_templates_sources_are_valid():
    """verify all template sources are valid"""
    templates = get_templates_list()
    valid_sources = {"builtin", "user"}

    for tmpl in templates:
        assert tmpl["source"] in valid_sources, (
            f"template '{tmpl['id']}' has invalid source '{tmpl['source']}'"
        )


# --- POST /api/extensions/reload ---


def test_reload_returns_ok():
    """verify reload endpoint returns success response"""
    result = reload_extensions()

    assert result["status"] == "ok"
    assert "message" in result


def test_reload_is_idempotent():
    """verify multiple reloads don't change state"""
    status_before = get_extensions_status()

    reload_extensions()
    reload_extensions()

    status_after = get_extensions_status()
    assert status_after["blocks"]["total"] == status_before["blocks"]["total"]
    assert status_after["templates"]["total"] == status_before["templates"]["total"]


# --- POST /api/extensions/blocks/{name}/validate ---


def test_validate_available_block():
    """verify validation of an available block returns valid=True"""
    blocks = get_blocks_list()
    available = next((b for b in blocks if b["available"]), None)
    assert available is not None, "need at least one available block"

    result = validate_block(available["type"])
    assert result["valid"] is True
    assert result["block"] == available["type"]


def test_validate_returns_block_name():
    """verify validation response includes block name"""
    blocks = get_blocks_list()
    assert len(blocks) > 0

    result = validate_block(blocks[0]["type"])
    assert "block" in result
    assert result["block"] == blocks[0]["type"]


def test_validate_nonexistent_block_returns_404():
    """verify validation of nonexistent block returns 404"""
    resp = httpx.post(
        f"{BASE_URL}/api/extensions/blocks/nonexistent_block_xyz/validate", timeout=10.0
    )
    assert resp.status_code == 404


# --- GET /api/extensions/blocks/{name}/dependencies ---


def test_dependencies_returns_list():
    """verify dependencies endpoint returns a list"""
    blocks = get_blocks_list()
    assert len(blocks) > 0

    result = get_block_dependencies(blocks[0]["type"])
    assert isinstance(result, list)


def test_dependencies_for_block_with_deps():
    """verify blocks with declared dependencies return dependency info"""
    blocks = get_blocks_list()
    block_with_deps = next(
        (b for b in blocks if b.get("dependencies") and len(b["dependencies"]) > 0), None
    )
    if block_with_deps is None:
        pytest.skip("no blocks with dependencies found")

    result = get_block_dependencies(block_with_deps["type"])
    assert len(result) > 0

    for dep in result:
        assert "name" in dep
        assert "installed" in dep


def test_dependencies_nonexistent_block_returns_404():
    """verify dependencies for nonexistent block returns 404"""
    resp = httpx.get(
        f"{BASE_URL}/api/extensions/blocks/nonexistent_block_xyz/dependencies", timeout=10.0
    )
    assert resp.status_code == 404


# --- cross-endpoint consistency ---


def test_available_blocks_are_all_valid():
    """verify all blocks marked available pass validation"""
    blocks = get_blocks_list()
    available_blocks = [b for b in blocks if b["available"]]

    for block in available_blocks:
        result = validate_block(block["type"])
        assert result["valid"] is True, (
            f"block '{block['type']}' is marked available but fails validation: {result}"
        )


def test_reload_then_validate_still_works():
    """verify validation works correctly after a reload"""
    blocks_before = get_blocks_list()
    available = next((b for b in blocks_before if b["available"]), None)
    assert available is not None

    reload_extensions()

    result = validate_block(available["type"])
    assert result["valid"] is True


if __name__ == "__main__":
    print("running extensions API e2e tests...")

    wait_for_server()
    cleanup_database()

    tests = [
        ("status structure", test_status_returns_valid_structure),
        ("status counts consistent", test_status_counts_are_consistent),
        ("status matches blocks list", test_status_block_count_matches_blocks_list),
        ("status matches templates list", test_status_template_count_matches_templates_list),
        ("blocks have required fields", test_blocks_list_returns_expected_fields),
        ("known builtin blocks exist", test_blocks_list_contains_known_builtin_blocks),
        ("new blocks registered", test_blocks_list_contains_new_blocks),
        ("block sources valid", test_blocks_sources_are_valid),
        ("block categories valid", test_blocks_categories_are_valid),
        ("templates have required fields", test_templates_list_returns_expected_fields),
        ("template sources valid", test_templates_sources_are_valid),
        ("reload returns ok", test_reload_returns_ok),
        ("reload is idempotent", test_reload_is_idempotent),
        ("validate available block", test_validate_available_block),
        ("validate returns block name", test_validate_returns_block_name),
        ("validate nonexistent 404", test_validate_nonexistent_block_returns_404),
        ("dependencies returns list", test_dependencies_returns_list),
        ("dependencies for block with deps", test_dependencies_for_block_with_deps),
        ("dependencies nonexistent 404", test_dependencies_nonexistent_block_returns_404),
        ("available blocks all valid", test_available_blocks_are_all_valid),
        ("reload then validate", test_reload_then_validate_still_works),
    ]

    for name, test_fn in tests:
        print(f"\ntest: {name}")
        try:
            test_fn()
            print("✓ passed")
        except BaseException as e:
            if type(e).__name__ == "Skipped":
                print(f"⊘ skipped: {e}")
            elif isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            else:
                print(f"✗ failed: {e}")

    cleanup_database()
    print("\n✅ all extensions API e2e tests completed!")
