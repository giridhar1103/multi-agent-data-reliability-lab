# Evaluation results

Mode: **demo**

Demo uses scripted policies, not LLMs. Shared fixture families are not independent real-world tasks.

| Topology | Runs | Cause accuracy | Outcome accuracy | Repair rate | Unnecessary repair rate | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| single | 24 | 100.0% | 100.0% | 100.0% | 0.0% | 3.011 |
| multi | 24 | 100.0% | 100.0% | 100.0% | 0.0% | 2.618 |

No claim of multi-agent superiority. Same tools and call ceilings; realized token use may differ.
Latency includes subprocess startup and synthetic regression execution.
Wilson intervals in JSON describe these runs only; correlated fixture seeds limit generalization.

Source commit before working-tree changes: 708e5c825451122dd03206d63a6dd889d15e3eda
