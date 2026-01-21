"""
helper functions for e2e tests.
handles database cleanup and initialization.
"""

import os
import time

import httpx


def get_headless_mode():
    """get headless mode from environment variable"""
    return os.getenv("E2E_HEADLESS", "true").lower() in ("true", "1", "yes")


def cleanup_database():
    """delete all pipelines, jobs, and records from the database"""
    base_url = "http://localhost:8000"

    try:
        # delete all records
        resp = httpx.delete(f"{base_url}/api/records", timeout=10.0)
        if resp.status_code >= 400:
            raise RuntimeError(f"failed to delete records: {resp.status_code}")

        # get all pipelines
        response = httpx.get(f"{base_url}/api/pipelines", timeout=10.0)
        if response.status_code >= 400:
            raise RuntimeError(f"failed to list pipelines: {response.status_code}")
        pipelines = response.json()

        # delete each pipeline
        for pipeline in pipelines:
            resp = httpx.delete(f"{base_url}/api/pipelines/{pipeline['id']}", timeout=10.0)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"failed to delete pipeline {pipeline['id']}: {resp.status_code}"
                )

        time.sleep(0.5)  # wait for cleanup to complete

    except Exception as e:
        raise RuntimeError(f"cleanup failed: {e}") from e


def wait_for_server(url: str = "http://localhost:8000/health", timeout: int = 30):
    """wait for server to be ready"""
    import urllib.error
    import urllib.request

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)

    return False


def get_pipeline_count():
    """get number of pipelines in database"""
    try:
        response = httpx.get("http://localhost:8000/api/pipelines", timeout=10.0)
        if response.status_code == 200:
            return len(response.json())
    except Exception as e:
        print(f"get_pipeline_count warning: {e}")
    return -1
