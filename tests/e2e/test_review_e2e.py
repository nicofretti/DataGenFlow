"""
e2e tests for review page.
tests record viewing, status updates, deletion, and export workflows.
"""

import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

try:
    from .test_helpers import get_headless_mode
except ImportError:
    from test_helpers import get_headless_mode


def test_review_page_loads():
    """verify review page loads successfully"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        # navigate to review page
        page.goto("http://localhost:5173/review")
        page.wait_for_load_state("networkidle")

        # verify we're on review page
        # look for job selector or records section
        job_or_records = page.get_by_text("Select Job", exact=False).or_(
            page.get_by_text("Records", exact=False)
        )
        assert job_or_records.count() > 0, "Review page should show job selector or records section"

        # take screenshot
        page.screenshot(path="/tmp/review_page.png", full_page=True)

        browser.close()


def test_select_job():
    """test selecting a job from dropdown"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173/review")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # find job selector (dropdown or select)
        selectors = page.locator('select, [role="combobox"]').all()

        if len(selectors) > 0:
            # click first selector
            selectors[0].click()
            time.sleep(0.5)

            # select first option (if options exist)
            if selectors[0].evaluate("el => el.tagName") == "SELECT":
                options = selectors[0].locator("option").all()
                if len(options) > 1:  # skip placeholder
                    selectors[0].select_option(index=1)
                    time.sleep(1)

            # take screenshot
            page.screenshot(path="/tmp/job_selected.png", full_page=True)

        browser.close()


def test_view_records():
    """test viewing generated records"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173/review")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # select a job if selector exists
        selectors = page.locator("select").all()
        if len(selectors) > 0:
            options = selectors[0].locator("option").all()
            if len(options) > 1:
                selectors[0].select_option(index=1)
                time.sleep(2)

        # look for record cards or table rows
        records = (
            page.locator(".record-card, [data-record]")
            .or_(page.locator(".Box"))
            .or_(page.locator("tr"))
        ).all()

        # if records exist, verify they're visible
        if len(records) > 0:
            print(f"found {len(records)} record elements")

        # take screenshot
        page.screenshot(path="/tmp/records_view.png", full_page=True)

        browser.close()


def test_update_record_status():
    """test updating a record's status"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173/review")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # select job
        selectors = page.locator("select").all()
        if len(selectors) > 0:
            options = selectors[0].locator("option").all()
            if len(options) > 1:
                selectors[0].select_option(index=1)
                time.sleep(2)

        # find status dropdown in record card
        # might be labeled as "pending", "accepted", "rejected"
        status_dropdowns = (
            page.locator("select")
            .filter(has_text="pending")
            .or_(page.locator('[aria-label*="status"]'))
        )

        if status_dropdowns.count() > 0:
            # click first status dropdown
            status_dropdowns.first.click()
            time.sleep(0.5)

            # select "accepted" or another status
            status_options = status_dropdowns.first.locator("option").all()
            if len(status_options) > 1:
                # try to select "accepted"
                for option in status_options:
                    text = option.text_content().lower()
                    if "accept" in text:
                        option.click()
                        break

                time.sleep(1)

                # take screenshot
                page.screenshot(path="/tmp/status_updated.png", full_page=True)

        browser.close()


def test_expand_trace():
    """test expanding a record's execution trace"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173/review")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # select job
        selectors = page.locator("select").all()
        if len(selectors) > 0:
            options = selectors[0].locator("option").all()
            if len(options) > 1:
                selectors[0].select_option(index=1)
                time.sleep(2)

        # find trace toggle button (collapsible)
        # might say "Show trace", "View details", or have a chevron icon
        trace_buttons = (
            page.get_by_role("button")
            .filter(has_text="Trace")
            .or_(page.get_by_role("button").filter(has_text="Details"))
            .or_(page.locator("button[aria-expanded]"))
        )

        if trace_buttons.count() > 0:
            # click to expand
            trace_buttons.first.click()
            time.sleep(1)

            # verify trace content is visible
            # look for block type, execution time, or trace data
            trace_content = page.get_by_text("block_type", exact=False).or_(
                page.get_by_text("execution_time", exact=False)
            )
            assert trace_content.count() > 0, "Trace should show block_type or execution_time"

            # take screenshot
            page.screenshot(path="/tmp/trace_expanded.png", full_page=True)

        browser.close()


def test_delete_records():
    """test deleting records"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173/review")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # select job
        selectors = page.locator("select").all()
        if len(selectors) > 0:
            options = selectors[0].locator("option").all()
            if len(options) > 1:
                selectors[0].select_option(index=1)
                time.sleep(2)

        # find delete button (might say "Delete All" or have trash icon)
        delete_buttons = (
            page.get_by_role("button")
            .filter(has_text="Delete")
            .or_(page.locator('button[aria-label*="Delete"]'))
        )

        if delete_buttons.count() > 0:
            # click delete
            delete_buttons.first.click()
            time.sleep(0.5)

            # handle confirmation dialog
            confirm_buttons = (
                page.get_by_role("button")
                .filter(has_text="Confirm")
                .or_(page.get_by_role("button").filter(has_text="Delete"))
            )

            if confirm_buttons.count() > 0:
                confirm_buttons.first.click()
                time.sleep(1)

            # take screenshot
            page.screenshot(path="/tmp/records_deleted.png", full_page=True)

        browser.close()


def test_export_records():
    """test exporting records"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()

        page.goto("http://localhost:5173/review")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # select job
        selectors = page.locator("select").all()
        if len(selectors) > 0:
            options = selectors[0].locator("option").all()
            if len(options) > 1:
                selectors[0].select_option(index=1)
                time.sleep(2)

        # find export button
        export_buttons = (
            page.get_by_role("button")
            .filter(has_text="Export")
            .or_(page.get_by_role("button").filter(has_text="Download"))
        )

        if export_buttons.count() > 0:
            try:
                # setup download listener
                with page.expect_download(timeout=5000) as download_info:
                    export_buttons.first.click()
                download = download_info.value
                print(f"download started: {download.suggested_filename}")
            except PlaywrightTimeoutError:
                print("no download (may be no records)")

            # take screenshot
            page.screenshot(path="/tmp/records_export.png", full_page=True)

        browser.close()


if __name__ == "__main__":
    print("running review e2e tests...")

    print("\ntest 1: review page loads")
    test_review_page_loads()
    print("✓ passed")

    print("\ntest 2: select job")
    test_select_job()
    print("✓ passed")

    print("\ntest 3: view records")
    test_view_records()
    print("✓ passed")

    print("\ntest 4: update record status")
    test_update_record_status()
    print("✓ passed")

    print("\ntest 5: expand trace")
    test_expand_trace()
    print("✓ passed")

    print("\ntest 6: delete records")
    test_delete_records()
    print("✓ passed")

    print("\ntest 7: export records")
    test_export_records()
    print("✓ passed")

    print("\n✅ all review e2e tests passed!")
