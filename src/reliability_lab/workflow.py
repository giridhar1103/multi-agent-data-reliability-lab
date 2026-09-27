import difflib
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from reliability_lab.contracts import Cause, Decision, Finding, Patch, Plan
from reliability_lab.execution import run_sql
from reliability_lab.fixtures import CORRECT_SQL, expected_rows, make_case
from reliability_lab.model import Model
from reliability_lab.store import Store, digest
from reliability_lab.telemetry import RUNS, stage


class State(TypedDict, total=False):
    case: dict
    evidence: dict
    plan: dict
    data_finding: dict
    code_finding: dict
    decision: dict
    patch: dict
    verification: dict
    result: dict


def observe(case: dict) -> dict:
    counts = Counter(r["order_id"] for r in case["refunds"])
    return {
        "data.profile": {
            "orders": len(case["orders"]),
            "refunds": len(case["refunds"]),
            "orders_with_multiple_refunds": sum(n > 1 for n in counts.values()),
            "cancelled_orders": sum(o["status"] == "cancelled" for o in case["orders"]),
            "refund_amounts_positive": all(r["amount"] > 0 for r in case["refunds"]),
        },
        "source.manifest": {
            "expected_orders": case["source_expected_orders"],
            "observed_orders": len(case["orders"]),
        },
        "metric.contract": case["contract"],
        "code.sql": case["sql"],
        "lineage.graph": case["lineage"],
        "current.output": run_sql(case, case["sql"]),
    }


def scripted_finding(evidence: dict, role: str) -> Finding:
    if "unavailable" in evidence["metric.contract"]:
        return Finding(
            cause=Cause.UNKNOWN,
            explanation="Approved business semantics are missing.",
            evidence_ids=["metric.contract"],
        )
    manifest = evidence["source.manifest"]
    if manifest["observed_orders"] != manifest["expected_orders"]:
        return Finding(
            cause=Cause.UPSTREAM_MISSING,
            explanation="Source row count differs from ingestion manifest.",
            evidence_ids=["source.manifest"],
        )
    sql = evidence["code.sql"].lower()
    if role == "data_investigator":
        return Finding(
            cause=Cause.UNKNOWN,
            explanation="Refund cardinality, cancelled orders, and positive refund amounts require checking the SQL grain and business contract.",
            evidence_ids=["data.profile", "metric.contract"],
        )
    if "left join refunds" in sql:
        return Finding(
            cause=Cause.DUPLICATE_JOIN,
            explanation="Joining raw one-to-many refunds repeats order gross before aggregation.",
            evidence_ids=["code.sql", "data.profile"],
        )
    if "o.gross +" in sql:
        return Finding(
            cause=Cause.REFUND_SIGN,
            explanation="Positive refunds are added instead of deducted.",
            evidence_ids=["code.sql", "metric.contract"],
        )
    if "where o.status" not in sql:
        return Finding(
            cause=Cause.STATUS_FILTER,
            explanation="Cancelled orders are included in completed-order revenue.",
            evidence_ids=["code.sql", "data.profile", "metric.contract"],
        )
    return Finding(
        cause=Cause.HEALTHY,
        explanation="No supported SQL defect in the checked contract.",
        evidence_ids=["code.sql", "metric.contract", "source.manifest"],
    )


def validate_citations(finding: Finding, evidence: dict):
    if not finding.evidence_ids or not set(finding.evidence_ids).issubset(evidence):
        raise ValueError("Agent must cite existing evidence IDs")


def verify(case: dict, sql: str) -> dict:
    checks = []
    # Candidate never sees oracle values or validation rows. Public synthetic holdouts,
    # not a sealed benchmark or proof of universal semantic correctness.
    for label, sample in [("incident_snapshot", case)] + [
        (f"regression_{i}", make_case("healthy", seed)) for i, seed in enumerate((103, 257, 991))
    ]:
        try:
            actual = run_sql(sample, sql)
            passed = actual["columns"] == ["order_day", "net_revenue"] and sorted(
                actual["rows"]
            ) == expected_rows(sample)
            checks.append({"name": label, "passed": passed})
        except Exception as exc:
            checks.append({"name": label, "passed": False, "error_type": type(exc).__name__})
    return {
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "method": "Independent Python oracle on incident and three unseen-in-context synthetic snapshots",
    }


def build_graph(store: Store, run_id: str, mode: str, topology: str, checkpointer):
    model = Model(store, run_id) if mode == "live" else None

    def plan(state):
        with stage(store, run_id, "planner", mode):
            context = {"incident": state["case"]["incident"], "evidence": state["evidence"]}
            value = (
                model.ask("planner", context, Plan)
                if model
                else Plan(
                    objective="Identify a supported cause and verify any proposed SQL repair.",
                    data_question="Check completeness, refunds, and cancellation distribution.",
                    code_question="Check aggregation grain, refund sign, and status filtering.",
                )
            )
            return {"plan": value.model_dump(mode="json")}

    def investigator(role, key):
        def node(state):
            with stage(store, run_id, role, mode):
                selected = {
                    k: v
                    for k, v in state["evidence"].items()
                    if (
                        k != "current.output"
                        if role == "code_investigator"
                        else k != "lineage.graph"
                    )
                }
                value = (
                    model.ask(role, {"plan": state["plan"], "evidence": selected}, Finding)
                    if model
                    else scripted_finding(state["evidence"], role)
                )
                validate_citations(value, state["evidence"])
                return {key: value.model_dump(mode="json")}

        return node

    def review(state):
        with stage(store, run_id, "reviewer" if topology == "multi" else "single_agent", mode):
            context = {"evidence": state["evidence"]}
            if topology == "multi":
                context.update(
                    {"data_finding": state["data_finding"], "code_finding": state["code_finding"]}
                )
            if model:
                decision = model.ask(
                    "evidence_reviewer" if topology == "multi" else "single_investigator",
                    context,
                    Decision,
                )
            else:
                finding = scripted_finding(state["evidence"], "code_investigator")
                action = (
                    "abstain"
                    if finding.cause in {Cause.UNKNOWN, Cause.UPSTREAM_MISSING}
                    else ("no_change" if finding.cause == Cause.HEALTHY else "repair")
                )
                decision = Decision(**finding.model_dump(), action=action)
            validate_citations(decision, state["evidence"])
            # Deterministic data-contract gate overrides unsupported repair proposals.
            manifest = state["evidence"]["source.manifest"]
            if (
                "unavailable" in state["case"]["contract"]
                or manifest["observed_orders"] != manifest["expected_orders"]
            ):
                decision.action = "abstain"
            if (
                decision.cause in {Cause.UNKNOWN, Cause.UPSTREAM_MISSING}
                and decision.action == "repair"
            ):
                decision.action = "abstain"
            return {"decision": decision.model_dump(mode="json")}

    def propose(state):
        with stage(store, run_id, "repair_proposer", mode):
            context = {
                "decision": state["decision"],
                "evidence": state["evidence"],
                "instruction": "Return one DuckDB SELECT over orders and refunds, output order_day and net_revenue. No other tables or I/O.",
            }
            patch = (
                model.ask("repair_proposer", context, Patch)
                if model
                else Patch(
                    sql=CORRECT_SQL,
                    rationale="Apply the approved grain, refund sign, and completed-order semantics.",
                )
            )
            return {"patch": patch.model_dump()}

    def verifier(state):
        with stage(store, run_id, "deterministic_verifier", mode) as detail:
            verification = verify(
                state["case"], state.get("patch", {}).get("sql", state["case"]["sql"])
            )
            detail["passed"] = verification["passed"]
            return {"verification": verification}

    def report(state):
        with stage(store, run_id, "report_export", mode):
            decision = state["decision"]
            verification = state.get("verification")
            outcome = "abstained"
            if decision["action"] == "repair":
                outcome = (
                    "verified_repair"
                    if verification and verification["passed"]
                    else "rejected_repair"
                )
            elif decision["action"] == "no_change":
                outcome = "no_change" if verification and verification["passed"] else "unresolved"
            proposed = state.get("patch", {}).get("sql")
            diff = "".join(
                difflib.unified_diff(
                    state["case"]["sql"].splitlines(True),
                    (proposed or state["case"]["sql"]).splitlines(True),
                    fromfile="models/daily_revenue.sql",
                    tofile="candidate/daily_revenue.sql",
                )
            )
            result = {
                "run_id": run_id,
                "mode": mode,
                "topology": topology,
                "outcome": outcome,
                "model": model.name if model else "scripted-policy (no LLM)",
                "decision": decision,
                "verification": verification,
                "evidence": state["evidence"],
                "plan": state.get("plan"),
                "findings": [state[k] for k in ("data_finding", "code_finding") if k in state],
                "original_sql": state["case"]["sql"],
                "candidate_sql": proposed,
                "diff": diff,
                "snapshot_hash": digest(
                    {"orders": state["case"]["orders"], "refunds": state["case"]["refunds"]}
                ),
                "code_hash": digest(state["case"]["sql"]),
                "limitations": "Synthetic SQL laboratory; verification covers specified snapshots only. No production repair is applied.",
            }
            store.artifact(run_id, "report.json", json.dumps(result, indent=2))
            store.artifact(run_id, "candidate.sql", proposed or "-- No patch proposed\n")
            store.artifact(run_id, "repair.diff", diff)
            store.artifact(
                run_id,
                "report.md",
                f"# Data reliability investigation\n\nMode: {mode}\n\nOutcome: {outcome}\n\n"
                f"{decision['explanation']}\n\nEvidence: {', '.join(decision['evidence_ids'])}\n\n"
                f"Snapshot: {result['snapshot_hash']}\n\n{result['limitations']}\n",
            )
            return {"result": result}

    graph = StateGraph(State)
    for name, node in [
        ("review", review),
        ("propose", propose),
        ("verify", verifier),
        ("report", report),
    ]:
        graph.add_node(name, node)
    if topology == "multi":
        graph.add_node("planner", plan)
        graph.add_node("data_investigator", investigator("data_investigator", "data_finding"))
        graph.add_node("code_investigator", investigator("code_investigator", "code_finding"))
        graph.add_edge(START, "planner")
        graph.add_edge("planner", "data_investigator")
        graph.add_edge("planner", "code_investigator")
        graph.add_edge(["data_investigator", "code_investigator"], "review")
    else:
        graph.add_edge(START, "review")
    graph.add_conditional_edges(
        "review",
        lambda s: {"repair": "propose", "no_change": "verify", "abstain": "report"}[
            s["decision"]["action"]
        ],
    )
    graph.add_edge("propose", "verify")
    graph.add_edge("verify", "report")
    graph.add_edge("report", END)
    return graph.compile(checkpointer=checkpointer)


def execute_run(store: Store, run_id: str):
    record = store.get(run_id)
    if record["status"] == "completed":
        return record["result"]
    request = record["request"]
    store.status(run_id, "running")
    connection = sqlite3.connect(str(store.root / "checkpoints.sqlite"), check_same_thread=False)
    try:
        checkpointer = SqliteSaver(connection)
        graph = build_graph(store, run_id, request["mode"], request["topology"], checkpointer)
        config = {"configurable": {"thread_id": run_id}, "recursion_limit": 20}
        checkpoint = graph.get_state(config)
        if checkpoint.values:
            inputs = None
        else:
            case = make_case(request["scenario"], request["seed"])
            with stage(store, run_id, "evidence_collection", request["mode"]):
                evidence = observe(case)
            inputs = {"case": case, "evidence": evidence}
        with stage(store, run_id, "investigation", request["mode"]):
            state = graph.invoke(inputs, config)
        result = state["result"]
        store.status(run_id, "completed", result=result)
        RUNS.labels(request["mode"], result["outcome"]).inc()
        return result
    except Exception as exc:
        store.status(run_id, "failed", error=f"{type(exc).__name__}: {exc}")
        RUNS.labels(request["mode"], "failed").inc()
        raise
    finally:
        connection.close()


def default_store():
    return Store(Path(os.getenv("LAB_DATA_DIR", "runs")))
