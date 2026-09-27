# Contributing

## **Local setup**

Install Python 3.11+, create a virtual environment, then install the locked runtime and development tools.

```sh
pip install -r requirements.lock
pip install -e ".[dev]"
ruff check src tests scripts
pytest -q
reliability-lab eval --seeds 11 --output artifacts/check
```

## **Adding an incident**

Include a fixture generator, an independent calculation of the expected result, and a counterexample that defeats an obvious but incorrect repair. Test that labels and expected results stay out of model prompts. Include the failure path as well as the successful one.

For a new agent, describe the decision it owns and how you will compare its contribution against the existing baseline.

Do not commit API keys, local run databases, private data, or screenshots containing credentials. README screenshots are captured from the actual synthetic demo with scripts/capture_ui.py.

## **Screenshots**

Use `scripts/capture_ui.py` for the workspace and `scripts/capture_observability.py` for Grafana and Jaeger. Both need the running application and Microsoft Edge. Set `LAB_CAPTURE_URL` if the app uses a port other than 8000. See the [validation guide](docs/validation.md) for the full capture workflow.

## **Private certificate authorities**

If your network uses TLS inspection, supply its trusted PEM certificate bundle as a temporary build secret:

```sh
docker build --secret id=pip_ca,src=/path/to/trusted-ca.pem -t multi-agent-data-reliability-lab-lab .
docker compose up -d --no-build
```

The certificate is available during the install step and is not copied into the image. Keep TLS verification enabled.

