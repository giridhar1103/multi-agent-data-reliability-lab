"""Short-lived SQL process. No credentials or model access; external access disabled."""

import json
import sys

import duckdb
import sqlglot
from sqlglot import exp


def validate_sql(sql: str) -> None:
    if len(sql) > 12000:
        raise ValueError("SQL exceeds size limit")
    trees = sqlglot.parse(sql, read="duckdb")
    if len(trees) != 1 or not isinstance(trees[0], exp.Select):
        raise ValueError("Exactly one SELECT is allowed")
    tree = trees[0]
    forbidden = (
        exp.Command,
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Create,
        exp.Drop,
        exp.Copy,
        exp.Into,
    )
    if any(isinstance(node, forbidden) for node in tree.walk()):
        raise ValueError("SQL mutation or command rejected")
    ctes = {cte.alias for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier) or table.db or table.catalog:
            raise ValueError("External or qualified tables rejected")
        if table.name not in {"orders", "refunds"} | ctes:
            raise ValueError("Table is outside the allowed snapshot")
    allowed_functions = {"SUM", "COUNT", "AVG", "MIN", "MAX", "ROUND", "COALESCE", "ABS", "CAST", "CASE", "IF"}
    for func in tree.find_all(exp.Func):
        if func.sql_name() not in allowed_functions:
            raise ValueError(f"Function {func.sql_name()} is not allowed")


def execute(payload: dict) -> dict:
    validate_sql(payload["sql"])
    con = duckdb.connect(
        config={
            "enable_external_access": "false",
            "memory_limit": "128MB",
            "threads": "1",
            "max_expression_depth": "100",
        }
    )
    try:
        con.execute(
            "CREATE TABLE orders(order_id INTEGER, order_day VARCHAR, gross DOUBLE, status VARCHAR)"
        )
        con.execute("CREATE TABLE refunds(order_id INTEGER, amount DOUBLE)")
        if payload["orders"]:
            con.executemany(
                "INSERT INTO orders VALUES (?, ?, ?, ?)",
                [
                    tuple(o[k] for k in ("order_id", "order_day", "gross", "status"))
                    for o in payload["orders"]
                ],
            )
        if payload["refunds"]:
            con.executemany(
                "INSERT INTO refunds VALUES (?, ?)",
                [(r["order_id"], r["amount"]) for r in payload["refunds"]],
            )
        cursor = con.execute(payload["sql"])
        rows = cursor.fetchmany(10001)
        if len(rows) > 10000:
            raise ValueError("Result row limit exceeded")
        return {"columns": [d[0] for d in cursor.description], "rows": rows}
    finally:
        con.close()


if __name__ == "__main__":
    try:
        result = execute(json.load(sys.stdin))
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
