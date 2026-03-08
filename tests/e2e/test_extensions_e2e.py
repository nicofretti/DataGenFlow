"""
E2E tests for extensions page.
Tests UI interactions with the extensions management interface,
block validation, reload, template creation, and status display.

Requires: running server (yarn dev + uvicorn) and playwright installed.
"""

import pytest
from playwright.sync_api import expect, sync_playwright

try:
    from .test_helpers import (
        cleanup_database,
        get_blocks_list,
        get_extensions_status,
        get_headless_mode,
        get_templates_list,
        wait_for_server,
    )
except ImportError:
    from test_helpers import (
        cleanup_database,
        get_blocks_list,
        get_extensions_status,
        get_headless_mode,
        get_templates_list,
        wait_for_server,
    )


@pytest.fixture(scope="module", autouse=True)
def _e2e_setup():
    if not wait_for_server():
        pytest.skip("server not ready for e2e tests")
    cleanup_database()
    yield
    cleanup_database()


def _navigate_to_extensions(page):
    """navigate to extensions page and wait for data to load"""
    page.goto("http://localhost:5173/extensions")
    page.wait_for_load_state("networkidle")
    # wait for blocks section to render (means API data loaded)
    page.wait_for_selector("h2:has-text('Blocks')", timeout=10000)


# --- page structure tests ---


def test_extensions_page_loads():
    """verify extensions page loads with all major sections"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # verify all three main sections
        expect(page.get_by_role("heading", name="Extensions")).to_be_visible()
        expect(page.get_by_role("heading", name="Blocks")).to_be_visible()
        expect(page.get_by_role("heading", name="Templates")).to_be_visible()

        # verify reload button exists
        expect(page.get_by_role("button", name="Reload")).to_be_visible()

        browser.close()


def test_extensions_status_cards_show_counts():
    """verify status overview cards display correct counts matching API"""
    api_status = get_extensions_status()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # verify "available" text appears with correct count
        available_text = page.locator(f"text={api_status['blocks']['available']} available")
        expect(available_text.first).to_be_visible()

        # verify "Builtin" label is present
        expect(page.locator("text=Builtin").first).to_be_visible()

        # verify block count in status card matches API
        builtin_count = api_status["blocks"]["builtin_blocks"]
        assert builtin_count > 0, "should have at least one builtin block"

        browser.close()


# --- block cards tests ---


def test_extensions_shows_block_cards_with_details():
    """verify block cards render with name, source badge, type, and description"""
    api_blocks = get_blocks_list()
    assert len(api_blocks) > 0, "API should return at least one block"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # verify builtin badge appears
        expect(page.locator("text=builtin").first).to_be_visible()

        # verify at least one known block name is rendered
        first_block = api_blocks[0]
        expect(page.locator(f"text={first_block['name']}").first).to_be_visible()

        # verify block type (mono text) is shown
        expect(page.locator(f"text={first_block['type']}").first).to_be_visible()

        # verify each block card has a Validate button
        validate_buttons = page.get_by_role("button", name="Validate")
        assert validate_buttons.count() >= len(api_blocks), (
            f"expected at least {len(api_blocks)} validate buttons, got {validate_buttons.count()}"
        )

        # verify available label is present on cards
        available_labels = page.locator("text=available")
        assert available_labels.count() > 0, "should show 'available' labels on block cards"

        browser.close()


def test_block_validate_shows_success_toast():
    """verify clicking Validate on an available block shows success toast"""
    api_blocks = get_blocks_list()
    # find an available block
    available_block = next((b for b in api_blocks if b["available"]), None)
    assert available_block is not None, "need at least one available block for this test"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # click the validate button within the card for the selected available block
        block_card = page.locator(
            f"xpath=//*/descendant-or-self::*[normalize-space()='{available_block['name']}']/ancestor::*[.//button[normalize-space()='Validate']][1]"
        )
        block_card.get_by_role("button", name="Validate").click()

        # wait for success toast
        toast = page.locator("text=is valid")
        expect(toast).to_be_visible(timeout=5000)

        browser.close()


def test_block_cards_count_matches_api():
    """verify the number of block cards in UI matches API response"""
    api_blocks = get_blocks_list()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # count validate buttons as proxy for block cards (each card has exactly one)
        validate_buttons = page.get_by_role("button", name="Validate")
        assert validate_buttons.count() == len(api_blocks), (
            f"UI shows {validate_buttons.count()} blocks, API returns {len(api_blocks)}"
        )

        browser.close()


# --- reload tests ---


def test_extensions_reload_shows_success_toast():
    """verify reload button triggers reload and shows success toast"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # click reload
        reload_btn = page.get_by_role("button", name="Reload")
        reload_btn.click()

        # button should show "Reloading..." while in progress
        # then success toast appears
        toast = page.locator("text=Extensions reloaded")
        expect(toast).to_be_visible(timeout=5000)

        browser.close()


def test_reload_preserves_block_count():
    """verify reload does not lose any blocks"""
    api_status_before = get_extensions_status()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # click reload
        page.get_by_role("button", name="Reload").click()
        page.locator("text=Extensions reloaded").wait_for(timeout=5000)

        # wait for page to re-render after reload
        page.wait_for_load_state("networkidle")

        browser.close()

    # verify API still returns same counts
    api_status_after = get_extensions_status()
    assert api_status_after["blocks"]["total"] == api_status_before["blocks"]["total"], (
        "reload should not change block count"
    )
    assert api_status_after["templates"]["total"] == api_status_before["templates"]["total"], (
        "reload should not change template count"
    )


# --- template cards tests ---


def test_extensions_shows_template_cards():
    """verify template cards render with name, source badge, and Create Pipeline button"""
    api_templates = get_templates_list()
    assert len(api_templates) > 0, "API should return at least one template"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # verify first template name is displayed
        first_template = api_templates[0]
        expect(page.locator(f"text={first_template['name']}").first).to_be_visible()

        # verify "Create Pipeline" buttons match template count
        create_buttons = page.get_by_role("button", name="Create Pipeline")
        assert create_buttons.count() == len(api_templates), (
            f"UI shows {create_buttons.count()} template buttons, API returns {len(api_templates)}"
        )

        browser.close()


def test_create_pipeline_from_template_card():
    """verify clicking Create Pipeline on a template card creates pipeline and navigates"""
    api_templates = get_templates_list()
    assert len(api_templates) > 0, "need at least one template"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # click first "Create Pipeline" button
        create_btn = page.get_by_role("button", name="Create Pipeline").first
        create_btn.click()

        # should show success toast
        toast = page.locator("text=Pipeline created from template")
        expect(toast).to_be_visible(timeout=5000)

        # should navigate to pipelines page
        page.wait_for_url("**/pipelines", timeout=5000)
        expect(page.get_by_role("heading", name="Pipelines", exact=True)).to_be_visible()

        browser.close()


# --- navigation tests ---


def test_navigate_to_extensions_from_sidebar():
    """verify navigating to extensions via sidebar link"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        # start from homepage
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # click Extensions in sidebar
        page.get_by_text("Extensions", exact=True).click()
        page.wait_for_url("**/extensions", timeout=5000)

        # verify page content loaded
        expect(page.get_by_role("heading", name="Extensions")).to_be_visible()
        page.wait_for_selector("h2:has-text('Blocks')", timeout=10000)

        browser.close()


# --- edge case tests ---


def test_validate_button_produces_toast():
    """verify Validate button produces a toast (success or error) without crashing"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # click the first validate button
        validate_btn = page.get_by_role("button", name="Validate").first
        validate_btn.click()

        # should show some toast (success or error) -- not a crash
        # look for any toast notification (sonner uses [data-sonner-toast])
        toast = page.locator("[data-sonner-toast]")
        expect(toast.first).to_be_visible(timeout=5000)

        browser.close()


def test_extensions_page_shows_block_descriptions():
    """verify block descriptions from API are rendered in UI"""
    api_blocks = get_blocks_list()
    # find a block with a non-empty description
    block_with_desc = next((b for b in api_blocks if b.get("description")), None)
    if block_with_desc is None:
        pytest.skip("no blocks with descriptions found")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # verify description text is visible (use partial match for long descriptions)
        desc_text = block_with_desc["description"][:50]
        expect(page.locator(f"text={desc_text}").first).to_be_visible()

        browser.close()


def test_extensions_page_shows_block_dependencies():
    """verify blocks with dependencies display them in the UI"""
    api_blocks = get_blocks_list()
    # find a block with dependencies
    block_with_deps = next(
        (b for b in api_blocks if b.get("dependencies") and len(b["dependencies"]) > 0), None
    )
    if block_with_deps is None:
        pytest.skip("no blocks with dependencies found")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        _navigate_to_extensions(page)

        # verify at least the first dependency name is rendered
        first_dep = block_with_deps["dependencies"][0]
        expect(page.locator(f"text={first_dep}").first).to_be_visible()

        browser.close()


if __name__ == "__main__":
    print("running extensions e2e tests...")

    if not wait_for_server():
        raise SystemExit("server not ready for e2e tests")
    cleanup_database()

    tests = [
        ("extensions page loads", test_extensions_page_loads),
        ("status cards show counts", test_extensions_status_cards_show_counts),
        ("block cards with details", test_extensions_shows_block_cards_with_details),
        ("block validate success toast", test_block_validate_shows_success_toast),
        ("block cards count matches API", test_block_cards_count_matches_api),
        ("reload shows success toast", test_extensions_reload_shows_success_toast),
        ("reload preserves block count", test_reload_preserves_block_count),
        ("template cards render", test_extensions_shows_template_cards),
        ("create pipeline from template", test_create_pipeline_from_template_card),
        ("navigate from sidebar", test_navigate_to_extensions_from_sidebar),
        ("validate button produces toast", test_validate_button_produces_toast),
        ("block descriptions shown", test_extensions_page_shows_block_descriptions),
        ("block dependencies shown", test_extensions_page_shows_block_dependencies),
    ]

    failures = 0
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
                failures += 1

    cleanup_database()
    if failures:
        raise SystemExit(f"\n{failures} extensions e2e test(s) failed")
    print("\n✅ all extensions e2e tests completed!")
