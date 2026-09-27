import json

import httpx
import pytest
from fastapi.testclient import TestClient

from reliability_lab.api import create_app
from reliability_lab.contracts import Finding, RunRequest
from reliability_lab.model import Model
from reliability_lab.store import Store
from reliability_lab.workflow import execute_run


def test_api_idempotency_conflict_validation_and_metrics(tmp_path):
    store = Store(tmp_path)
    client = TestClient(create_app(store))
    headers = {"Idempotency-Key": "same"}
    first = client.post("/api/runs", json={}, headers=headers)
    assert first.status_code == 202
    assert client.post("/api/runs", json={}, headers=headers).json() == first.json()
    assert client.post("/api/runs", json={"seed": 12}, headers=headers).status_code == 409
    assert client.post("/api/runs", json={"scenario": "../../secret"}).status_code == 422
    assert client.get("/api/runs/missing").status_code == 404
    assert "lab_runs" in client.get("/metrics").text
    assert client.get("/").status_code == 200


def test_model_strict_json_cache_budget_and_no_credentials_in_events(tmp_path, monkeypatch):
    store = Store(tmp_path)
    run_id = store.create(RunRequest(mode="live").model_dump())
    monkeypatch.setenv("LAB_MAX_MODEL_CALLS", "1")
    monkeypatch.setenv("LAB_API_KEY", "test-secret")
    calls = []
    real_client = httpx.Client

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "cause": "unknown",
                                    "explanation": "Insufficient evidence",
                                    "evidence_ids": ["metric.contract"],
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler))
    )
    model = Model(store, run_id)
    assert model.ask("review", {}, Finding).cause.value == "unknown"
    model.ask("review", {}, Finding)
    assert len(calls) == 1
    with pytest.raises(RuntimeError, match="budget"):
        model.ask("other-role", {}, Finding)
    assert "test-secret" not in json.dumps(store.events(run_id))


def test_live_failure_is_not_reported_as_demo_success(tmp_path, monkeypatch):
    store = Store(tmp_path)
    monkeypatch.setattr(
        Model, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("unavailable"))
    )
    run_id = store.create(RunRequest(mode="live").model_dump())
    with pytest.raises(RuntimeError):
        execute_run(store, run_id)
    assert store.get(run_id)["status"] == "failed"
    assert store.get(run_id)["result"] is None


def test_job_claim_and_recovery(tmp_path):
    store = Store(tmp_path)
    run_id = store.create(RunRequest().model_dump())
    assert store.claim() == run_id
    assert store.claim() is None
    store.recover()
    assert store.claim() == run_id
