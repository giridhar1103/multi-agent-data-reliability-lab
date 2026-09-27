"""Capture actual running UI, exercise tabs, and verify mobile overflow."""
import json
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

OUT = Path("docs/images")
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1180}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8000")
    page.get_by_role("button", name="Investigate incident").click()
    page.locator("#badge").filter(has_text="VERIFIED REPAIR").wait_for(timeout=60000)
    for tab, name in [("trace", "investigation"), ("repair", "sql-repair"), ("checks", "verification")]:
        page.locator(f'[data-tab="{tab}"]').click()
        page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(OUT / "mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Mobile overflow"
    assert not errors, errors
    browser.close()
with httpx.Client() as client:
    runs = client.get("http://127.0.0.1:8000/api/runs").json()
    completed = next(r for r in runs if r["outcome"] == "verified_repair")
    detail = client.get(f"http://127.0.0.1:8000/api/runs/{completed['id']}").json()
    Path("docs/examples").mkdir(parents=True, exist_ok=True)
    Path("docs/examples/investigation.json").write_text(json.dumps(detail["result"], indent=2), encoding="utf-8")
print("Captured real UI; tabs and mobile overflow passed.")

