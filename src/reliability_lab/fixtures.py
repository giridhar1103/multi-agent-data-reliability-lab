"""Synthetic fixtures. Ground truth is consumed by evals, never included in agent context."""

import random

from reliability_lab.contracts import Cause

CONTRACT = (
    "Return one row per order_day, columns order_day and net_revenue. "
    "Net revenue is completed-order gross less positive refund amounts. "
    "Exclude cancelled orders. An order can have multiple refunds; count its gross once. "
    "Keep completed orders with no refunds. Amounts use the same currency. "
    "Missing source records cannot be repaired by guessing values."
)

CORRECT_SQL = """SELECT o.order_day,
ROUND(SUM(o.gross - COALESCE(r.refunded, 0)), 2) AS net_revenue
FROM orders o
LEFT JOIN (SELECT order_id, SUM(amount) AS refunded FROM refunds GROUP BY order_id) r
ON o.order_id = r.order_id
WHERE o.status = 'completed'
GROUP BY o.order_day ORDER BY o.order_day"""

BROKEN_JOIN = """SELECT o.order_day,
ROUND(SUM(o.gross - COALESCE(r.amount, 0)), 2) AS net_revenue
FROM orders o LEFT JOIN refunds r ON o.order_id = r.order_id
WHERE o.status = 'completed'
GROUP BY o.order_day ORDER BY o.order_day"""


def make_case(scenario: str, seed: int) -> dict:
    scenario = Cause(scenario)
    rng = random.Random(seed)
    orders, refunds = [], []
    for i in range(1, 31):
        orders.append(
            {
                "order_id": i,
                "order_day": f"2026-09-{1 + (i % 5):02d}",
                "gross": float(rng.randrange(20, 201)),
                "status": "cancelled" if i % 7 == 0 else "completed",
            }
        )
        if i % 3 == 0:
            for _ in range(2 if i % 6 == 0 else 1):
                refunds.append({"order_id": i, "amount": float(rng.randrange(1, 10))})
    sql = CORRECT_SQL
    expected_count = len(orders)
    if scenario == Cause.DUPLICATE_JOIN:
        sql = BROKEN_JOIN
    elif scenario == Cause.REFUND_SIGN:
        sql = CORRECT_SQL.replace("o.gross -", "o.gross +")
    elif scenario == Cause.STATUS_FILTER:
        sql = CORRECT_SQL.replace("WHERE o.status = 'completed'", "")
    elif scenario == Cause.UPSTREAM_MISSING:
        orders = orders[:-5]
    contract = (
        CONTRACT
        if scenario != Cause.UNKNOWN
        else (
            "Produce daily revenue. The approved treatment of refunds and cancelled orders is unavailable."
        )
    )
    return {
        "orders": orders,
        "refunds": refunds,
        "sql": sql,
        "contract": contract,
        "source_expected_orders": expected_count,
        "lineage": [
            ["orders", "daily_revenue"],
            ["refunds", "daily_revenue"],
            ["daily_revenue", "revenue_dashboard"],
        ],
        "incident": "Check whether the daily revenue output is reliable. Diagnose and propose a repair only when supported.",
    }


def expected_rows(case: dict) -> list[list]:
    # Independent Python oracle: never uses candidate SQL or generated expected values.
    totals = {}
    for order in case["orders"]:
        if order["status"] == "completed":
            refunded = sum(
                r["amount"] for r in case["refunds"] if r["order_id"] == order["order_id"]
            )
            day = order["order_day"]
            totals[day] = totals.get(day, 0) + order["gross"] - refunded
    return [[day, round(value, 2)] for day, value in sorted(totals.items())]
