# Multi-Agent Data Reliability Lab

**Investigate broken metrics, challenge the diagnosis, and verify a proposed SQL repair.**

[![quality](https://github.com/giridhar1103/multi-agent-data-reliability-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/giridhar1103/multi-agent-data-reliability-lab/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Docker](https://img.shields.io/badge/Docker-local%20first-bcf781)
![License](https://img.shields.io/badge/license-MIT-blue)

Stateful multi-agent orchestration, typed evidence, restricted SQL execution, independent verification, restart recovery, and reproducible evaluations for the data domain.

> **First-release scope:** synthetic commerce data and SQL transformations. Demo mode uses scripted policies; live mode calls your configured model. Arbitrary dbt-project ingestion and production warehouse repair are not implemented yet.

![Actual investigation interface](docs/images/investigation.png)

## Run locally

Requires Docker with Linux containers. No API key is needed for the deterministic demo.

```sh
git clone https://github.com/giridhar1103/multi-agent-data-reliability-lab.git
cd multi-agent-data-reliability-lab
docker compose up --build -d --wait
```

Open **http://localhost:8000**, choose an incident, and click **Investigate incident**.

```sh
docker compose exec lab reliability-lab run --scenario duplicate_join
docker compose exec lab reliability-lab eval --output /data/evals
docker compose down
```

Run data persists in a named volume. The application exports candidates for review; it does not apply repairs or modify source data.

## The incident

A revenue model joins orders directly to a one-to-many refunds table. Orders with multiple refunds contribute their gross amount multiple times. The SQL executes successfully while producing incorrect revenue.

The lab collects evidence, runs independent data/code investigations, reviews the diagnosis, proposes a repair, and checks it against an independent Python oracle on the incident and three additional regression snapshots.

Other cases cover refund signs, cancelled orders, healthy controls, missing records, and unavailable metric definitions. Missing records and semantics trigger abstention instead of invented repairs.

## Architecture

![Implemented system](docs/images/architecture.svg)

| Component | Engineering responsibility |
|---|---|
| LangGraph | Persisted state, parallel specialists, fan-in review, conditional outcomes |
| Pydantic | Strict output contracts and evidence-reference validation |
| Model adapter | BYOK/local HTTP inference, bounded retry, persisted call budget, parsed-response cache |
| SQL executor | AST allowlist, external I/O disabled, short-lived processes, deadlines, row limits |
| Independent verifier | Expected values calculated without candidate SQL or an LLM judge |
| SQLite + artifacts | Durable runs, atomic claims, checkpoints, idempotency, input hashes |
| FastAPI + CLI | Local run UI, typed API, exported JSON/Markdown/SQL/diffs |
| OTel + Prometheus | Stage traces, outcomes, duration histograms, model usage |
| CI | Tests, lint, synthetic evaluation, container startup and execution |

[Architecture and boundaries](docs/architecture.md) · [Evaluation methodology](docs/evaluation.md) · [Security](SECURITY.md)

## Power it with your model

Copy `.env.example` to `.env`. Configure a chat-completions-compatible endpoint:

```dotenv
LAB_MODEL_BASE_URL=https://your-provider.example/v1
LAB_MODEL=your-model-id
LAB_API_KEY=your-key
LAB_MAX_MODEL_CALLS=8
LAB_MAX_OUTPUT_TOKENS=1200
```

Run `docker compose up -d` and select **Live** in the interface, or:

```sh
docker compose exec lab reliability-lab run --mode live --scenario duplicate_join
```

For local Ollama inference, use `http://host.docker.internal:11434/v1`, an installed model ID, and an empty API key. The adapter uses Chat Completions with JSON-object output; not every vendor's native API is compatible. A failed live run remains failed, with no demo fallback.

Credentials stay on the server. Live model context goes to the configured endpoint. A local application does not imply local inference.

An optional host-only **headless Codex benchmark transport** uses the author's CLI sign-in. It is documented in [evaluation.md](docs/evaluation.md) and is not required by the Docker application.

## Observability

Set this in `.env`:

```dotenv
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://jaeger:4318/v1/traces
```

```sh
docker compose --profile observability up -d --wait
```

| Surface | URL | Inspect |
|---|---|---|
| Application | http://localhost:8000 | Persisted events, evidence, SQL, verification |
| API reference | http://localhost:8000/docs | Run creation, status, resume, artifacts |
| Jaeger | http://localhost:16686 | reliability-lab traces and spans |
| Prometheus | http://localhost:9090 | Outcomes, latency, provider usage |
| Grafana | http://localhost:3000 | Provisioned Reliability Lab dashboard |

All services bind to loopback. Grafana allows anonymous **viewing** in this local profile; do not expose it publicly. Jaeger uses ephemeral development storage; application events persist independently. Prometheus counters reset on process restart.

## Evaluation with honest labels

The recorded demo suite contains **48 runs**: six incident families × four data seeds × two topologies. All 48 produced the expected synthetic outcome, with **zero model calls**. This establishes integration behavior for authored policies, not LLM accuracy.

- [Recorded demo results](docs/evals/demo/results.md) and [raw rows](docs/evals/demo/results.json).
- [Methodology, limitations, and live commands](docs/evaluation.md).
- [Example evidence bundle](docs/examples/investigation.json).

Both topologies receive the same available evidence and model-call ceiling, but realized token use differs. The suite does not establish multi-agent superiority.

![Actual candidate SQL](docs/images/sql-repair.png)

![Actual independent verification](docs/images/verification.png)

## Develop and test

```sh
python -m venv .venv
# Activate .venv for your shell, then:
pip install -r requirements.lock
pip install -e ".[dev]"
pytest -q
ruff check src tests scripts
reliability-lab serve
```

Tests cover incident outcomes, external/malicious SQL rejection, deadlines, independent verification, API conflicts, checkpoint resume, model caches/budgets, and live-provider failures.

Runtime versions are pinned in `requirements.lock`; the Python image is digest-pinned. For a network with a private TLS-inspection CA, use a trusted PEM bundle as an ephemeral build secret:

```sh
docker build --secret id=pip_ca,src=/path/to/trusted-ca.pem -t multi-agent-data-reliability-lab-lab .
docker compose up -d --no-build
```

## Next milestones

- Versioned adapter for real dbt manifests, run results, contracts, and DuckDB snapshots.
- Independently authored incidents, schema variations, multi-fault cases, and held-out families.
- Bounded diagnostic-tool selection and evidence-driven replanning, with measured ablations.
- Cancellation, distributed leases, and Postgres when concurrent usage warrants them.
- Pinned-model comparisons, token-normalized tradeoffs, and published failure analyses.

## Design references

Inspired by [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [CrewAI's Flow-first approach](https://docs.crewai.com/en/concepts/production-architecture), [R&D-Agent](https://github.com/microsoft/RD-Agent), [WrenAI semantic context](https://github.com/Canner/WrenAI), and [multi-agent failure research](https://arxiv.org/abs/2503.13657). Implementation and visual assets are original.

MIT licensed. See [CONTRIBUTING.md](CONTRIBUTING.md).
