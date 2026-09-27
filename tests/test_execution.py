import subprocess

import pytest

from reliability_lab.execution import run_sql
from reliability_lab.fixtures import BROKEN_JOIN, CORRECT_SQL, expected_rows, make_case
from reliability_lab.sql_worker import validate_sql
from reliability_lab.workflow import verify


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE orders",
        "SELECT 1; SELECT 2",
        "SELECT * FROM read_csv_auto('/etc/passwd')",
        "SELECT * FROM sqlite_scan('secret.db','users')",
        "SELECT * FROM other_table",
        "SELECT * FROM information_schema.tables",
        "COPY orders TO '/tmp/export.csv'",
        "SELECT * FROM range(100000000)",
        "SELECT current_setting('access_mode')",
        "SELECT * INTO exported FROM orders",
    ],
)
def test_rejects_commands_external_io_and_unapproved_functions(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)


def test_actual_query_is_checked_against_independent_oracle():
    case = make_case("duplicate_join", 19)
    assert run_sql(case, BROKEN_JOIN)["rows"] != expected_rows(case)
    assert run_sql(case, CORRECT_SQL)["rows"] == expected_rows(case)
    assert verify(case, CORRECT_SQL)["passed"]
    assert not verify(case, BROKEN_JOIN)["passed"]


def test_conditional_refund_aggregation_is_supported():
    case = make_case("healthy", 11)
    sql = CORRECT_SQL.replace("SUM(amount)", "SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END)")
    assert verify(case, sql)["passed"]


def test_hardcoded_incident_answer_fails_regressions():
    case = make_case("healthy", 19)
    literal = " UNION ALL ".join(
        f"SELECT '{day}' AS order_day, {amount} AS net_revenue"
        for day, amount in expected_rows(case)
    )
    # The conservative query grammar rejects UNION roots, avoiding a bypass.
    assert not verify(case, literal)["passed"]


def test_sql_deadline(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("worker", 0.01)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        run_sql(make_case("healthy", 1), CORRECT_SQL, timeout=0.01)
