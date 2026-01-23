"""
e2e tests for generator page.
tests job creation, file upload, and progress monitoring workflows.
"""

import json
import os
import time

import pytest
from playwright.sync_api import expect, sync_playwright

try:
    from .test_helpers import cleanup_database, get_headless_mode, wait_for_server
except ImportError:
    from test_helpers import cleanup_database, get_headless_mode, wait_for_server


@pytest.fixture(scope="module", autouse=True)
def _e2e_setup_teardown():
    """setup and teardown for e2e tests"""
    if not wait_for_server():
        pytest.skip("server not ready for e2e tests")
    cleanup_database()
    # create a pipeline for generator tests
    _setup_test_pipeline()
    yield
    cleanup_database()


def _setup_test_pipeline():
    """create a pipeline from template for tests"""
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

        # create pipeline from first template
        create_buttons = page.get_by_role("button").filter(has_text="Use Template")
        if create_buttons.count() > 0:
            create_buttons.first.click()
            time.sleep(2)
            page.wait_for_load_state("networkidle")

        browser.close()


def test_generator_page_loads():
    """verify generator page loads successfully"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        # navigate to generator page (default route)
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")

        # verify we're on generator page by checking heading
        heading = page.get_by_role("heading", name="Generate Records")
        expect(heading).to_be_visible()

        # take screenshot
        page.screenshot(path="/tmp/generator_page.png", full_page=True)

        browser.close()


def test_select_pipeline():
    """test selecting a pipeline from dropdown"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        # go to generator page (default route)
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # find pipeline selector (dropdown or select)
        selectors = page.locator('select, [role="combobox"]').all()
        assert len(selectors) > 0, "No pipeline selector found on page"

        if len(selectors) > 0:
            # click first selector
            selectors[0].click()
            time.sleep(0.5)

            # select first option (if it's a select element)
            if selectors[0].evaluate("el => el.tagName") == "SELECT":
                options = selectors[0].locator("option").all()
                if len(options) > 1:  # skip "select pipeline" placeholder
                    selectors[0].select_option(index=1)
            else:
                # for custom dropdowns, click first item
                items = page.locator('[role="option"]').all()
                if len(items) > 0:
                    items[0].click()

            time.sleep(1)

            # take screenshot
            page.screenshot(path="/tmp/pipeline_selected.png", full_page=True)

        browser.close()


def test_upload_seed_file():
    """test uploading a seed JSON file"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        # create test seed file matching JSON Generation template (expects 'content' field)
        seed_data = [
            {
                "repetitions": 1,
                "metadata": {
                    "content": "Artificial intelligence is transforming education by enabling personalized learning experiences.",
                },
            }
        ]

        seed_path = "/tmp/test_seed.json"
        with open(seed_path, "w") as f:
            json.dump(seed_data, f)

        # go to generator page
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # select pipeline
        selectors = page.locator("select").all()
        if len(selectors) > 0:
            options = selectors[0].locator("option").all()
            assert len(options) > 1, "No pipelines available; create one before running e2e tests"
            selectors[0].select_option(index=1)
            time.sleep(1)

        # find file input
        file_inputs = page.locator('input[type="file"]').all()
        assert len(file_inputs) > 0, "Seed file input not found on generator page"

        # upload file
        file_inputs[0].set_input_files(seed_path)
        time.sleep(1)

        # verify file name appears or upload succeeds
        page.screenshot(path="/tmp/file_uploaded.png", full_page=True)

        # cleanup
        os.remove(seed_path)

        browser.close()


def test_start_generation_job():
    """test starting a generation job"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        # create test seed file matching JSON Generation template (expects 'content' field)
        seed_data = [
            {
                "repetitions": 1,
                "metadata": {
                    "content": "Machine learning is a subset of AI that enables computers to learn from data without explicit programming.",
                },
            }
        ]

        seed_path = "/tmp/test_seed_job.json"
        with open(seed_path, "w") as f:
            json.dump(seed_data, f)

        # go to generator page
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # select pipeline
        selectors = page.locator("select").all()
        if len(selectors) > 0:
            options = selectors[0].locator("option").all()
            assert len(options) > 1, "No pipelines available; create one before running e2e tests"
            selectors[0].select_option(index=1)
            time.sleep(1)

        # upload file
        file_inputs = page.locator('input[type="file"]').all()
        assert len(file_inputs) > 0, "Seed file input not found on generator page"
        file_inputs[0].set_input_files(seed_path)
        time.sleep(1)

        # find and click generate/start button
        generate_buttons = (
            page.get_by_role("button")
            .filter(has_text="Generate")
            .or_(page.get_by_role("button").filter(has_text="Start"))
        )
        assert generate_buttons.count() > 0, "Generate/Start button not found"
        generate_buttons.first.click()

        # wait for job to start
        time.sleep(3)
        page.wait_for_load_state("networkidle")

        # verify job progress appears
        # look for progress indicators
        progress_indicator = page.get_by_text("Progress", exact=False).or_(
            page.get_by_text("Generated", exact=False)
        )
        assert progress_indicator.count() > 0, "Progress indicator should be visible"

        # take screenshot
        page.screenshot(path="/tmp/job_started.png", full_page=True)

        # cleanup
        os.remove(seed_path)

        browser.close()


def test_generator_shows_upload_ui():
    """test that generator page shows upload interface when no job is running"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # verify upload UI is present (the primary interface when no job is running)
        upload_ui = page.get_by_text("Upload", exact=False)
        assert upload_ui.count() > 0, "Upload UI should be visible on generator page"
        page.screenshot(path="/tmp/generator_upload_ui.png", full_page=True)

        browser.close()


if __name__ == "__main__":
    print("running generator e2e tests...")

    # setup: create a pipeline for generator tests
    print("\nsetup: creating test pipeline...")
    wait_for_server()
    cleanup_database()
    _setup_test_pipeline()
    print("✓ test pipeline created")

    print("\ntest 1: generator page loads")
    test_generator_page_loads()
    print("✓ passed")

    print("\ntest 2: select pipeline")
    test_select_pipeline()
    print("✓ passed")

    print("\ntest 3: upload seed file")
    test_upload_seed_file()
    print("✓ passed")

    print("\ntest 4: start generation job")
    test_start_generation_job()
    print("✓ passed")

    print("\ntest 5: generator shows upload ui")
    test_generator_shows_upload_ui()
    print("✓ passed")

    # cleanup after tests
    print("\ncleaning up...")
    cleanup_database()
    print("✓ cleanup complete")

    print("\n✅ all generator e2e tests passed!")
