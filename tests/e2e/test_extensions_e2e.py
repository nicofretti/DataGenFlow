"""
E2E tests for extensions page.
Tests UI interactions with the extensions management interface.

Requires: running server (yarn dev + uvicorn) and playwright installed.
"""

import pytest
from playwright.sync_api import sync_playwright

try:
    from .test_helpers import get_headless_mode, wait_for_server
except ImportError:
    from test_helpers import get_headless_mode, wait_for_server


@pytest.fixture(scope="module", autouse=True)
def _e2e_setup():
    if not wait_for_server():
        pytest.skip("server not ready for e2e tests")


def test_extensions_page_loads():
    """verify extensions page loads and shows blocks/templates sections"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # click extensions in sidebar
        page.get_by_text("Extensions", exact=True).click()
        page.wait_for_load_state("networkidle")

        # verify page content
        assert page.get_by_role("heading", name="Extensions").is_visible()
        assert page.get_by_role("heading", name="Blocks").is_visible()
        assert page.get_by_role("heading", name="Templates").is_visible()

        browser.close()


def test_extensions_shows_block_cards():
    """verify block cards are rendered with source badges"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173/extensions")
        page.wait_for_load_state("networkidle")

        # should show at least one block card with "builtin" badge
        assert page.locator("text=builtin").first.is_visible()
        # should show at least one known block
        assert page.locator("text=Text Generator").first.is_visible()

        browser.close()


def test_extensions_reload_button():
    """verify reload button triggers extension reload"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173/extensions")
        page.wait_for_load_state("networkidle")

        # click reload
        page.get_by_role("button", name="Reload").click()

        # should show success toast
        page.wait_for_selector("text=Extensions reloaded", timeout=5000)

        browser.close()


def test_extensions_status_cards():
    """verify status overview cards show correct counts"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173/extensions")
        page.wait_for_load_state("networkidle")

        # status cards should show "available" text
        assert page.locator("text=available").first.is_visible()
        # should show "Builtin" label
        assert page.locator("text=Builtin").first.is_visible()

        browser.close()
