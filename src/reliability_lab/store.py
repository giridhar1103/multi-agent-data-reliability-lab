import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "lab.sqlite"
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS runs(
              id TEXT PRIMARY KEY, request TEXT NOT NULL, status TEXT NOT NULL,
              created REAL NOT NULL, result TEXT, error TEXT,
              idempotency_key TEXT UNIQUE, request_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, role TEXT NOT NULL,
              started REAL NOT NULL, duration_ms REAL NOT NULL,
              status TEXT NOT NULL, detail TEXT NOT NULL, trace_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS calls(
              run_id TEXT NOT NULL, call_key TEXT NOT NULL, response TEXT NOT NULL,
              PRIMARY KEY(run_id, call_key)
            );
            CREATE TABLE IF NOT EXISTS budgets(
              run_id TEXT PRIMARY KEY, reserved INTEGER NOT NULL
            );
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def create(self, request: dict, key: str | None = None) -> str:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if key:
                row = db.execute(
                    "SELECT id, request_hash FROM runs WHERE idempotency_key=?", (key,)
                ).fetchone()
                if row:
                    if row["request_hash"] != digest(request):
                        raise ValueError("Idempotency key already used for a different request")
                    return row["id"]
            run_id = uuid.uuid4().hex
            db.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    json.dumps(request),
                    "queued",
                    time.time(),
                    None,
                    None,
                    key,
                    digest(request),
                ),
            )
            return run_id

    def get(self, run_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        out = dict(row)
        out["request"] = json.loads(out["request"])
        out["result"] = json.loads(out["result"]) if out["result"] else None
        return out

    def list_runs(self) -> list[dict]:
        with self.connect() as db:
            ids = db.execute("SELECT id FROM runs ORDER BY created DESC LIMIT 100").fetchall()
        return [self.get(row["id"]) for row in ids]

    def status(self, run_id: str, status: str, result=None, error=None):
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET status=?, result=?, error=? WHERE id=?",
                (status, json.dumps(result) if result is not None else None, error, run_id),
            )

    def recover(self):
        # Single application worker. Only invoke on process startup with one ASGI worker.
        with self.connect() as db:
            db.execute("UPDATE runs SET status='queued' WHERE status='running'")

    def claim(self) -> str | None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT id FROM runs WHERE status='queued' ORDER BY created LIMIT 1"
            ).fetchone()
            if row:
                db.execute("UPDATE runs SET status='running' WHERE id=?", (row["id"],))
                return row["id"]
        return None

    def event(self, run_id, role, started, duration_ms, status, detail, trace_id):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(run_id,role,started,duration_ms,status,detail,trace_id) VALUES(?,?,?,?,?,?,?)",
                (run_id, role, started, duration_ms, status, json.dumps(detail), trace_id),
            )

    def events(self, run_id):
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE run_id=? ORDER BY started,id", (run_id,)
            ).fetchall()
        return [dict(row) | {"detail": json.loads(row["detail"])} for row in rows]

    def cached(self, run_id, key):
        with self.connect() as db:
            row = db.execute(
                "SELECT response FROM calls WHERE run_id=? AND call_key=?", (run_id, key)
            ).fetchone()
        return json.loads(row["response"]) if row else None

    def cache(self, run_id, key, value):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO calls VALUES(?,?,?)", (run_id, key, json.dumps(value))
            )

    def reserve_call(self, run_id, limit):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO budgets VALUES(?,0)", (run_id,))
            used = db.execute("SELECT reserved FROM budgets WHERE run_id=?", (run_id,)).fetchone()[
                0
            ]
            if used >= limit:
                raise RuntimeError("Model-call budget exhausted")
            db.execute("UPDATE budgets SET reserved=reserved+1 WHERE run_id=?", (run_id,))

    def artifact(self, run_id, name, content):
        folder = self.root / run_id
        folder.mkdir(exist_ok=True)
        path = folder / name
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
        return str(path)
