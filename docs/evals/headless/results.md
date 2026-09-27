# Evaluation results

Mode: **live**

Demo uses scripted policies, not LLMs. Shared fixture families are not independent real-world tasks.

| Topology | Runs | Cause accuracy | Outcome accuracy | Repair rate | Unnecessary repair rate | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| single | 6 | 100.0% | 100.0% | 100.0% | 0.0% | 19.373 |
| multi | 6 | 33.3% | 33.3% | 66.7% | 0.0% | 28.536 |

No claim of multi-agent superiority. Same tools and call ceilings; realized token use may differ.
Latency includes subprocess startup and synthetic regression execution.
Wilson intervals in JSON describe these runs only; correlated fixture seeds limit generalization.

Source commit before working-tree changes: b65cda936a415bf14b9b6a0b5d449c9f5c2e7721
