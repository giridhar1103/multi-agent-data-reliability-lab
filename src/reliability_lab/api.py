import asyncio
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from reliability_lab.contracts import RunRequest
from reliability_lab.workflow import default_store, execute_run

STATIC = Path(__file__).parent / "static"


def create_app(store=None):
    store = store or default_store()
    stop = threading.Event()

    def work():
        while not stop.is_set():
            run_id = store.claim()
            if run_id:
                try:
                    execute_run(store, run_id)
                except Exception:
                    pass  # Failure is persisted and exposed by run detail + metrics.
            else:
                stop.wait(0.25)

    @asynccontextmanager
    async def lifespan(app):
        stop.clear()
        store.recover()
        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        yield
        stop.set()
        await asyncio.to_thread(thread.join, 2)

    app = FastAPI(title="Multi-Agent Data Reliability Lab", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/health")
    def health():
        return {"status": "ok", "default_mode": os.getenv("LAB_MODE", "demo")}

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/api/runs", status_code=202)
    def create_run(request: RunRequest, idempotency_key: str | None = Header(default=None)):
        if idempotency_key and len(idempotency_key) > 128:
            raise HTTPException(400, "Idempotency key too long")
        try:
            run_id = store.create(request.model_dump(), idempotency_key)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"run_id": run_id, "status_url": f"/api/runs/{run_id}"}

    @app.get("/api/runs")
    def list_runs():
        return [
            {
                "id": r["id"],
                "status": r["status"],
                "created": r["created"],
                "request": r["request"],
                "outcome": (r["result"] or {}).get("outcome"),
            }
            for r in store.list_runs()
        ]

    def get_run(run_id):
        try:
            return store.get(run_id)
        except KeyError as exc:
            raise HTTPException(404, "Run not found") from exc

    @app.get("/api/runs/{run_id}")
    def detail(run_id: str):
        return get_run(run_id) | {"events": store.events(run_id)}

    @app.post("/api/runs/{run_id}/resume", status_code=202)
    def resume(run_id: str):
        run = get_run(run_id)
        if run["status"] != "failed":
            raise HTTPException(409, "Only failed runs can be resumed")
        store.status(run_id, "queued")
        return {"run_id": run_id}

    @app.get("/api/runs/{run_id}/artifacts/{name}")
    def artifact(run_id: str, name: str):
        get_run(run_id)
        if name not in {"report.json", "report.md", "candidate.sql", "repair.diff"}:
            raise HTTPException(404, "Unknown artifact")
        path = store.root / run_id / name
        if not path.is_file():
            raise HTTPException(404, "Artifact not ready")
        return FileResponse(path, filename=name)

    return app
