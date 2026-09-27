import sqlite3

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

from reliability_lab.contracts import RunRequest
from reliability_lab.fixtures import make_case
from reliability_lab.store import Store
from reliability_lab.workflow import build_graph, execute_run, observe


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("duplicate_join", "verified_repair"),
        ("refund_sign", "verified_repair"),
        ("status_filter", "verified_repair"),
        ("healthy", "no_change"),
        ("upstream_missing", "abstained"),
        ("unknown", "abstained"),
    ],
)
def test_incident_outcomes_and_evidence(tmp_path, scenario, expected):
    store = Store(tmp_path)
    run_id = store.create(RunRequest(scenario=scenario).model_dump())
    result = execute_run(store, run_id)
    assert result["outcome"] == expected
    assert set(result["decision"]["evidence_ids"]).issubset(result["evidence"])
    assert (tmp_path / run_id / "report.json").is_file()
    assert store.get(run_id)["status"] == "completed"
    assert "scenario" not in result["evidence"]
    assert result["mode"] == "demo"


def test_completed_runs_are_idempotent(tmp_path):
    store = Store(tmp_path)
    run_id = store.create(RunRequest(scenario="unknown").model_dump())
    first = execute_run(store, run_id)
    count = len(store.events(run_id))
    assert execute_run(store, run_id) == first
    assert len(store.events(run_id)) == count


def test_resume_uses_checkpoint_without_repeating_completed_nodes(tmp_path):
    store = Store(tmp_path)
    run_id = store.create(RunRequest().model_dump())
    case = make_case("duplicate_join", 11)
    with sqlite3.connect(tmp_path / "checkpoints.sqlite", check_same_thread=False) as connection:
        graph = build_graph(store, run_id, "demo", "multi", SqliteSaver(connection))
        config = {"configurable": {"thread_id": run_id}}
        graph.invoke({"case": case, "evidence": observe(case)}, config, interrupt_after=["planner"])
        assert graph.get_state(config).next
    assert execute_run(store, run_id)["outcome"] == "verified_repair"
    assert len([e for e in store.events(run_id) if e["role"] == "planner"]) == 1


def test_single_agent_baseline_has_no_specialist_fanout(tmp_path):
    store = Store(tmp_path)
    run_id = store.create(RunRequest(scenario="healthy", topology="single").model_dump())
    assert execute_run(store, run_id)["outcome"] == "no_change"
    assert "data_investigator" not in [e["role"] for e in store.events(run_id)]
