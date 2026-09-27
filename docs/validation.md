# Release validation

Validated on 2026-09-27. This release targets local synthetic SQL incident investigation, not autonomous production repair.

| Check | Evidence |
|---|---|
| Unit/integration suite | 27 tests passed locally; GitHub Actions test job passed |
| Lint | `ruff check src tests scripts` passed |
| Demo evaluation | 48/48 expected outcomes; zero model calls; [recorded rows](evals/demo/results.json) |
| Live inference | 12 attempted cases, eight expected outcomes and four inference failures; [analysis](evals/headless/README.md) |
| Revised evaluation metadata | Additional 12/12 deterministic smoke cases passed |
| Container | Linux CI built image, waited for health, and executed a verified repair |
| Browser | Real Edge captures; trace, repair, verification tabs and mobile overflow checks |
| Observability | Prometheus reported verified repair, no-change and abstention counters; Jaeger returned an eight-span investigation; real Grafana and Jaeger screenshots saved |

[Initial green CI run](https://github.com/giridhar1103/multi-agent-data-reliability-lab/actions/runs/36304491562) covers both the test and container jobs. Subsequent commits are checked by the same workflow.

## Reproduce the visual evidence

With the app and optional observability profile running, install the development environment and Playwright with a local Microsoft Edge browser. Run:

```sh
python scripts/capture_ui.py
python scripts/capture_observability.py
python scripts/render_evaluation.py
```

Set `LAB_CAPTURE_URL=http://127.0.0.1:8001` when using an alternate host port. Capture scripts submit demo incidents and save actual screenshots and JSON evidence. The evaluation figure reads committed result rows; it does not invent scores.

## Interpretation and limits

The deterministic demo proves authored integration behavior. Live results are exploratory and include all failures; the CLI model was not pinned and these cases do not establish multi-agent superiority. The verifier covers fixture snapshots and cannot prove arbitrary SQL correctness. The local service uses one worker, SQLite persistence, and loopback access. SQL restrictions reduce exposure but are not a complete hostile-code security boundary. See [security boundaries](../SECURITY.md) and [evaluation methodology](evaluation.md).
