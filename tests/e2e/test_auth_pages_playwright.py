import os

import pytest


pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Error as PlaywrightError, sync_playwright  # noqa: E402


@pytest.mark.e2e
def test_login_page_smoke():
    if os.getenv("RUN_E2E") != "1":
        pytest.skip("Set RUN_E2E=1 to run Playwright e2e tests")

    base_url = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except PlaywrightError as exc:
            pytest.skip(f"Chromium not available: {exc}")

        page = browser.new_page()
        page.goto(f"{base_url}/login", wait_until="networkidle")
        assert page.locator("h2.title").inner_text().strip().lower() == "login"
        browser.close()

