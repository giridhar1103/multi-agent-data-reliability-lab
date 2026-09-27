# Exploratory headless inference run

Recorded on 2026-09-27 using the host's signed-in Codex CLI, `LAB_MODEL_TRANSPORT=codex`, `LAB_MODEL=codex-default`, seed 11, and the default eight-call ceiling. The CLI-selected model was **not pinned or recorded**. This is remote inference through a local CLI, not an on-device model benchmark.

The [raw results](results.json) retain all twelve attempted cases. Single-agent completed 6/6 with expected outcomes. Multi-agent completed 2/6 with expected outcomes; the remaining four failed at the inference boundary. Saved application errors report `Live model call failed (RuntimeError); no demo fallback`. The underlying CLI error output was not retained, so the precise cause cannot be established from these artifacts. Account usage exhaustion was observed in the surrounding development session but is not a proven per-run diagnosis.

Do not interpret the resulting 100% versus 33.3% outcome scores as an architecture ranking: sequential execution, an unpinned model, provider failures, and six authored fixture families confound the comparison. Failed cases remain in the denominator. Zero unnecessary repairs does not establish safety when some controls failed before producing a decision.

Reported model calls count usage events (9 single, 13 multi), not every attempted subprocess. Token totals include CLI context overhead and omit usage from failed calls. Latency includes failures and is not a clean speed comparison. Raw report values are preserved without retroactive changes.

Next benchmark: pin a model/version, retain sanitized provider error categories, interleave topologies, repeat independent incidents, report completion and conditional quality separately, and measure budget-normalized cost. The existing run demonstrates the end-to-end live path and its failure handling; it does not establish production accuracy.
