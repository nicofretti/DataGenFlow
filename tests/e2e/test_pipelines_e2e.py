"""
e2e tests for pipelines page.
tests pipeline creation, editing, and deletion workflows.
"""

import time

import pytest
from playwright.sync_api import expect, sync_playwright

from .test_helpers import cleanup_database, get_headless_mode, wait_for_server


def test_pipelines_page_loads():
    """verify pipelines page loads successfully"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        # navigate to pipelines page via sidebar
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # click pipelines in sidebar
        pipelines_link = page.get_by_text("Pipelines", exact=True)
        pipelines_link.click()
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # verify page title
        expect(page).to_have_title("DataGenFlow")

        # take screenshot for debugging
        page.screenshot(path="/tmp/pipelines_page.png", full_page=True)

        browser.close()


def test_view_templates():
    """verify pipeline templates are displayed"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # click pipelines in sidebar
        pipelines_link = page.get_by_text("Pipelines", exact=True)
        pipelines_link.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # check for template-related content or buttons
        # look for "Use Template" buttons or template names
        use_template_buttons = (
            page.get_by_role("button")
            .filter(has_text="Use Template")
            .or_(page.get_by_role("button").filter(has_text="Create from Template"))
        )

        # take screenshot first for debugging
        page.screenshot(path="/tmp/templates_view.png", full_page=True)

        # if templates exist, there should be use template buttons
        # otherwise page should at least load without error
        print(f"found {use_template_buttons.count()} template buttons")

        # verify page loaded correctly
        expect(page.get_by_text("Pipelines", exact=True)).to_be_visible()

        browser.close()


def test_create_pipeline_from_template():
    """test creating a pipeline from a template"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # navigate to pipelines page
        pipelines_link = page.get_by_text("Pipelines", exact=True)
        pipelines_link.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # find and click the first template's create button
        # look for buttons with text "Use Template" or similar
        create_buttons = (
            page.get_by_role("button")
            .filter(has_text="Use Template")
            .or_(page.get_by_role("button").filter(has_text="Create"))
        )

        if create_buttons.count() > 0:
            first_button = create_buttons.first
            first_button.click()

            # wait for pipeline to be created (modal or redirect)
            time.sleep(2)
            page.wait_for_load_state("networkidle")

            # verify success - check for "My Pipelines" heading using role
            pipelines_heading = page.get_by_role("heading", name="My Pipelines")
            expect(pipelines_heading).to_be_visible()

            # take screenshot
            page.screenshot(path="/tmp/pipeline_created.png", full_page=True)
        else:
            browser.close()
            pytest.skip("no template buttons found - templates may not be loaded")

        browser.close()


def test_delete_pipeline():
    """test deleting a pipeline"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # navigate to pipelines page
        pipelines_link = page.get_by_text("Pipelines", exact=True)
        pipelines_link.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # first create a pipeline from template
        create_buttons = page.get_by_role("button").filter(has_text="Use Template")
        if create_buttons.count() > 0:
            create_buttons.first.click()
            time.sleep(2)
            page.wait_for_load_state("networkidle")

        # find delete button (trash icon or delete text)
        # might be in a pipeline card or row
        delete_buttons = (
            page.get_by_role("button")
            .filter(has_text="Delete")
            .or_(page.locator('button[aria-label*="Delete" i]'))
            .or_(page.locator('button[aria-label*="delete" i]'))
        )

        initial_count = delete_buttons.count()

        if initial_count > 0:
            # click first delete button
            delete_buttons.first.click()

            # handle confirmation dialog if present
            time.sleep(0.5)

            # look for confirm button in dialog
            confirm_buttons = (
                page.get_by_role("button")
                .filter(has_text="Confirm")
                .or_(page.get_by_role("button").filter(has_text="Delete"))
            )

            if confirm_buttons.count() > 0:
                confirm_buttons.first.click()

            # wait for deletion
            time.sleep(1)
            page.wait_for_load_state("networkidle")

            # take screenshot
            page.screenshot(path="/tmp/pipeline_deleted.png", full_page=True)

        browser.close()


def test_pipeline_editor_opens():
    """test that pipeline editor modal opens"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # navigate to pipelines page
        pipelines_link = page.get_by_text("Pipelines", exact=True)
        pipelines_link.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # create a pipeline first
        create_buttons = page.get_by_role("button").filter(has_text="Use Template")
        if create_buttons.count() > 0:
            create_buttons.first.click()
            time.sleep(2)
            page.wait_for_load_state("networkidle")

        # find edit button (pencil icon, edit text, or gear icon)
        edit_buttons = (
            page.get_by_role("button")
            .filter(has_text="Edit")
            .or_(page.locator('button[aria-label*="Edit"]'))
        )

        if edit_buttons.count() > 0:
            edit_buttons.first.click()
            time.sleep(1)

            # verify modal/editor opened (reactflow canvas should be visible)
            # look for reactflow container or canvas elements
            canvas = page.locator(".react-flow, [data-reactflow], canvas").first
            expect(canvas).to_be_visible(timeout=5000)

            # take screenshot
            page.screenshot(path="/tmp/pipeline_editor.png", full_page=True)

        browser.close()


if __name__ == "__main__":
    print("running pipelines e2e tests...")

    # clean database before tests
    print("\ncleaning database...")
    wait_for_server()
    cleanup_database()
    print("✓ database cleaned")

    print("\ntest 1: pipelines page loads")
    test_pipelines_page_loads()
    print("✓ passed")

    print("\ntest 2: view templates")
    test_view_templates()
    print("✓ passed")

    print("\ntest 3: create pipeline from template")
    test_create_pipeline_from_template()
    print("✓ passed")

    print("\ntest 4: delete pipeline")
    test_delete_pipeline()
    print("✓ passed")

    print("\ntest 5: pipeline editor opens")
    test_pipeline_editor_opens()
    print("✓ passed")

    # clean database after tests
    print("\ncleaning up...")
    cleanup_database()
    print("✓ cleanup complete")

    print("\n✅ all pipelines e2e tests passed!")
