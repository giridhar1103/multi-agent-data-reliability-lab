# Contributing

Install Python 3.11+, create a virtual environment, then install the locked runtime and development tools.

```sh
pip install -r requirements.lock
pip install -e ".[dev]"
ruff check src tests
pytest -q
reliability-lab eval --seeds 11 --output artifacts/check
```

For a new incident, contribute a fixture generator, independently calculated expected behavior, at least one counterexample for a naive repair, and a test that labels/oracle outputs do not enter model prompts. Include failure cases. Do not add a new agent without a measurable responsibility and a baseline comparison.

Do not commit API keys, local run databases, private data, or screenshots containing credentials. README screenshots are captured from the actual synthetic demo with scripts/capture_ui.py.

