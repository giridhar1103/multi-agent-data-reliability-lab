import argparse
import json
from pathlib import Path

from reliability_lab.contracts import RunRequest
from reliability_lab.evaluation import evaluate
from reliability_lab.workflow import default_store, execute_run


def main():
    parser = argparse.ArgumentParser(description="Local multi-agent data reliability lab")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument(
        "--scenario",
        default="duplicate_join",
        choices=[
            "duplicate_join",
            "refund_sign",
            "status_filter",
            "healthy",
            "upstream_missing",
            "unknown",
        ],
    )
    run.add_argument("--mode", choices=["demo", "live"], default="demo")
    run.add_argument("--topology", choices=["single", "multi"], default="multi")
    run.add_argument("--seed", type=int, default=11)
    evaluation = commands.add_parser("eval")
    evaluation.add_argument("--mode", choices=["demo", "live"], default="demo")
    evaluation.add_argument("--output", type=Path, default=Path("artifacts/evals"))
    evaluation.add_argument("--seeds", default="11,23,47,89")
    resume = commands.add_parser("resume")
    resume.add_argument("run_id")
    commands.add_parser("serve")
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn

        uvicorn.run("reliability_lab.api:create_app", factory=True, host="0.0.0.0", port=8000)
    elif args.command == "eval":
        report = evaluate(args.output, args.mode, tuple(int(v) for v in args.seeds.split(",")))
        print(json.dumps(report["summary"], indent=2))
        if any(s["failures"] for s in report["summary"].values()):
            raise SystemExit(1)
    else:
        store = default_store()
        run_id = (
            args.run_id
            if args.command == "resume"
            else store.create(
                RunRequest(
                    scenario=args.scenario, mode=args.mode, topology=args.topology, seed=args.seed
                ).model_dump()
            )
        )
        result = execute_run(store, run_id)
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "outcome": result["outcome"],
                    "report": str(store.root / run_id / "report.md"),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
