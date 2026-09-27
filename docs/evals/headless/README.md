# Live inference results

A twelve-case run recorded on **2026-09-27** using the signed-in Codex CLI. Configuration: `LAB_MODEL_TRANSPORT=codex`, `LAB_MODEL=codex-default`, seed 11, and an eight-call budget per investigation. The CLI selected the model; its exact version was not recorded. Inference ran remotely through the host CLI.

## **Results**

| Topology | Expected outcomes | Inference failures | Calls with usage records |
|---|---:|---:|---:|
| Single-agent | 6/6 | 0 | 9 |
| Multi-agent | 2/6 | 4 | 13 |

[Full report](results.md) · [Raw rows](results.json)

The four failed runs stopped at the inference boundary. The saved error is `Live model call failed (RuntimeError); no demo fallback`. The underlying CLI output was not retained, so the specific cause is unresolved.

## **How to read these numbers**

These results do not rank the architectures. Runs were executed sequentially, the model was unpinned, and four cases failed before returning a decision. All twelve attempts remain in the denominator. A zero unnecessary-repair count is also inconclusive when some control cases failed to finish.

Call counts cover responses with usage records, not every attempted subprocess. Token totals include CLI context overhead and exclude unreported usage from failed calls. Reported latency includes failures. The original result files are unchanged.

## **Next comparison**

Pin the model version, interleave the two topologies, and retain sanitized provider error categories. Use independently written incidents and report completion rate alongside decision quality. Compare token budgets as well as outcomes.
