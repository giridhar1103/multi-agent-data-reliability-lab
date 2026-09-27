"""Verify actual telemetry and capture the provisioned local dashboards."""
import json
import os
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

out = Path("docs/images")
base = os.getenv("LAB_CAPTURE_URL", "http://127.0.0.1:8000")
out.mkdir(parents=True, exist_ok=True)
with httpx.Client(timeout=15) as client:
    run_ids = []
    for scenario in ("duplicate_join", "healthy", "upstream_missing"):
        response = client.post(f"{base}/api/runs", json={"scenario": scenario})
        response.raise_for_status()
        run_id = response.json()["run_id"]
        run_ids.append(run_id)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            run = client.get(f"{base}/api/runs/{run_id}").json()
            if run["status"] not in {"queued", "running"}:
                assert run["result"], run
                break
            time.sleep(1)
        else:
            raise TimeoutError(run_id)
    deadline = time.monotonic() + 60
    while True:
        metrics = client.get("http://127.0.0.1:9090/api/v1/query", params={"query": "lab_runs_total"}).json()
        traces = client.get("http://127.0.0.1:16686/api/traces", params={"service": "reliability-lab", "limit": 20}).json()
        if metrics.get("data", {}).get("result") and traces.get("data"):
            break
        if time.monotonic() > deadline:
            raise TimeoutError("Telemetry did not reach both backends")
        time.sleep(2)
    trace = max(traces["data"], key=lambda t: len(t["spans"]))
    evidence = {"run_ids": run_ids, "prometheus": metrics, "trace_id": trace["traceID"],
                "span_count": len(trace["spans"]), "operations": [s["operationName"] for s in trace["spans"]]}
    Path("docs/examples/observability.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1080}, device_scale_factor=1)
    page.goto("http://127.0.0.1:3000/d/reliability-lab/multi-agent-data-reliability-lab?orgId=1&from=now-15m&to=now")
    page.get_by_text("Completed runs by mode and outcome", exact=True).wait_for(timeout=60000)
    page.wait_for_timeout(8000)
    page.screenshot(path=str(out / "grafana.png"), full_page=True)
    page.goto(f"http://127.0.0.1:16686/trace/{trace['traceID']}")
    page.get_by_text("reliability-lab", exact=False).first.wait_for(timeout=60000)
    page.wait_for_timeout(3000)
    page.screenshot(path=str(out / "jaeger.png"), full_page=True)
    browser.close()
print(json.dumps(evidence, indent=2))
