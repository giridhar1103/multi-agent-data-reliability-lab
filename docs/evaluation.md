# Evaluation methodology

## **Reproduce**

```sh
reliability-lab eval --mode demo --output artifacts/demo
reliability-lab eval --mode live --seeds 11 --output artifacts/live
```

The default suite contains six incident families × four data seeds × two topologies = 48 runs. Families cover duplicate joins, incorrect refund signs, cancelled-order leakage, healthy controls, missing upstream rows, and missing semantic definitions.

Demo policies are authored for these known families. Their success establishes fixture and pipeline behavior, not LLM quality, generalization, or multi-agent superiority.

## **Ground truth and verification**

Evaluation labels live outside the model context. Agents receive the incident observations, current SQL, and business contract. A separate Python calculation computes expected daily values. Candidate SQL must match the incident snapshot and three additional synthetic snapshots. This catches some overfitting and semantic errors, but the fixtures and verifier are public and are not a sealed benchmark.

Changing numeric seeds within a fixed family tests different data values, not new classes of incident. A future stronger benchmark must add independently authored SQL, new schema names, multi-fault incidents, withheld incident families, and real dbt transformation projects.

## **Metrics**

- Exact cause accuracy across all requested runs.
- Correct terminal outcome, including no-change and abstention.
- Verified repair rate over the three repairable families.
- Unnecessary repair rate over healthy, missing-data, and ambiguous controls.
- Failed runs, wall time, provider-reported tokens, and model call counts.
- Wilson intervals for outcome accuracy; correlated fixtures limit their interpretation.

Failures remain in the denominator. Benchmark rows contain scenario, seed, topology, outcome, duration, model calls, and token totals. Reports identify mode, environment, and code version. Provider failures are not converted into successful demo runs.

The two topologies share tool evidence and call ceilings, but realized calls, prompts, and tokens differ. Results are not a matched-token causal experiment. Demo latency mostly measures process and graph overhead. This suite alone cannot establish which architecture performs better.

## **Live inference**

Configure LAB_MODEL_BASE_URL, LAB_MODEL, and LAB_API_KEY for an HTTP chat-completions-compatible endpoint. The default transport requests JSON and validates against Pydantic schemas, with at most one retry per call and a persistent run-wide call ceiling.

To run the optional host transport with a signed-in Codex CLI:

```sh
export LAB_MODEL_TRANSPORT=codex
export LAB_MODEL=codex-default
export LAB_MODEL_TIMEOUT=180
reliability-lab eval --mode live --seeds 11 --output artifacts/codex
```

This optional transport runs headlessly, disables shell and web tools, uses a fresh temporary directory and output schema, and rejects observed tool actions. It is not a locally hosted model and is not included in the Docker image. codex-default identifies an unpinned CLI default; publish an exact explicit model ID for comparable future results.

[Official non-interactive documentation](https://developers.openai.com/codex/noninteractive)
and [configuration reference](https://developers.openai.com/codex/config-reference).

