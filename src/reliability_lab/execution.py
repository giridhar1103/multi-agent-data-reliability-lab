import json
import os
import subprocess
import sys

from reliability_lab.sql_worker import validate_sql


def run_sql(case: dict, sql: str, timeout: float = 8) -> dict:
    validate_sql(sql)
    # Child receives only synthetic rows and SQL, never provider credentials.
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PYTHONPATH"}
    }
    result = subprocess.run(
        [sys.executable, "-m", "reliability_lab.sql_worker"],
        input=json.dumps({"orders": case["orders"], "refunds": case["refunds"], "sql": sql}),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        check=False,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("SQL worker exited without a valid result") from exc
    if result.returncode or "error" in data:
        raise ValueError(data.get("error", "SQL execution failed"))
    return data
