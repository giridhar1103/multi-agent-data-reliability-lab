import json
import math
import os
import platform
import subprocess
import time
from pathlib import Path

from reliability_lab.contracts import Cause, RunRequest
from reliability_lab.store import Store
from reliability_lab.workflow import execute_run


def wilson(successes, count):
    if not count:
        return None
    z = 1.96
    p = successes / count
    denominator = 1 + z * z / count
    centre = (p + z * z / (2 * count)) / denominator
    radius = z * math.sqrt((p * (1 - p) + z * z / (4 * count)) / count) / denominator
    return [round(max(0, centre - radius), 4), round(min(1, centre + radius), 4)]


def evaluate(output: Path, mode="demo", seeds=(11, 23, 47, 89), topologies=("single", "multi")):
    output.mkdir(parents=True, exist_ok=True)
    store = Store(output / "runs")
    rows = []
    expected_action = {
        "duplicate_join": "verified_repair",
        "refund_sign": "verified_repair",
        "status_filter": "verified_repair",
        "healthy": "no_change",
        "upstream_missing": "abstained",
        "unknown": "abstained",
    }
    for topology in topologies:
        for scenario in Cause:
            for seed in seeds:
                request = RunRequest(
                    scenario=scenario.value, seed=seed, mode=mode, topology=topology
                )
                run_id = store.create(request.model_dump())
                started = time.perf_counter()
                try:
                    result = execute_run(store, run_id)
                    cause = result["decision"]["cause"]
                    outcome = result["outcome"]
                    error = None
                except Exception as exc:
                    cause, outcome, error = None, "failed", type(exc).__name__
                events = store.events(run_id)
                usage = [e["detail"].get("usage", {}) for e in events if e["role"] == "model_usage"]
                rows.append(
                    {
                        "run_id": run_id,
                        "scenario": scenario.value,
                        "seed": seed,
                        "topology": topology,
                        "mode": mode,
                        "cause_correct": cause == scenario.value,
                        "outcome_correct": outcome == expected_action[scenario.value],
                        "outcome": outcome,
                        "error": error,
                        "latency_seconds": round(time.perf_counter() - started, 3),
                        "model_calls": len(usage),
                        "provider_tokens": sum(u.get("total_tokens", 0) for u in usage),
                    }
                )
    summary = {}
    for topology in topologies:
        group = [row for row in rows if row["topology"] == topology]
        correct = sum(row["outcome_correct"] for row in group)
        repairable = [
            row
            for row in group
            if row["scenario"] in {"duplicate_join", "refund_sign", "status_filter"}
        ]
        controls = [
            row for row in group if row["scenario"] in {"healthy", "upstream_missing", "unknown"}
        ]
        summary[topology] = {
            "runs": len(group),
            "cause_accuracy": sum(row["cause_correct"] for row in group) / len(group),
            "outcome_accuracy": correct / len(group),
            "outcome_wilson_95": wilson(correct, len(group)),
            "verified_repair_rate": sum(row["outcome"] == "verified_repair" for row in repairable)
            / len(repairable),
            "unnecessary_repair_rate": sum(
                row["outcome"] in {"verified_repair", "rejected_repair"} for row in controls
            )
            / len(controls),
            "failures": sum(row["error"] is not None for row in group),
            "mean_latency_seconds": round(
                sum(row["latency_seconds"] for row in group) / len(group), 3
            ),
            "model_calls": sum(row["model_calls"] for row in group),
            "provider_tokens": sum(row["provider_tokens"] for row in group),
        }
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = "unavailable"
    report = {
        "mode": mode,
        "scope": "Synthetic fixture integration evaluation",
        "warning": "Demo uses scripted policies, not LLMs. Shared fixture families are not independent real-world tasks.",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "git_commit": commit,
            "model": os.getenv("LAB_MODEL", "unspecified") if mode == "live" else None,
            "transport": os.getenv("LAB_MODEL_TRANSPORT", "http") if mode == "live" else None,
            "max_model_calls": int(os.getenv("LAB_MAX_MODEL_CALLS", "8")),
        },
        "seeds": list(seeds),
        "summary": summary,
        "rows": rows,
    }
    (output / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Evaluation results",
        "",
        f"Mode: **{mode}**",
        "",
        report["warning"],
        "",
        "| Topology | Runs | Cause accuracy | Outcome accuracy | Repair rate | Unnecessary repair rate | Mean seconds |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, s in summary.items():
        lines.append(
            f"| {name} | {s['runs']} | {s['cause_accuracy']:.1%} | {s['outcome_accuracy']:.1%} | {s['verified_repair_rate']:.1%} | {s['unnecessary_repair_rate']:.1%} | {s['mean_latency_seconds']} |"
        )
    lines += [
        "",
        "No claim of multi-agent superiority. Same tools and call ceilings; realized token use may differ.",
        "Model calls count responses with usage events; transport failures can add attempts without reported tokens.",
        "Latency includes subprocess startup and synthetic regression execution.",
        "Wilson intervals in JSON describe these runs only; correlated fixture seeds limit generalization.",
        "",
        f"Source commit before working-tree changes: {commit}",
        "",
    ]
    (output / "results.md").write_text("\n".join(lines), encoding="utf-8")
    return report
