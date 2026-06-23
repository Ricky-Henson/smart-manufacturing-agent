# Skill: get_lot_stats

**Purpose.** Return deterministic parametric summary statistics for one lot, so
the agent can talk about a lot without inventing numbers.

**Input**
| field | type | notes |
|---|---|---|
| `lot_id` | string | must exist under `DATA_DIR` |

**Output**
| field | type | notes |
|---|---|---|
| `lot_id` | string | echoes input |
| `n_die` | int | dies measured |
| `params` | object | per-param `{mean, std, min, max, limit, n_breach}` |

**Verifier (`verify.py`).** Asserts: `lot_id` echoes input; `n_die >= 0`; every
param block has the required keys; `n_breach <= n_die`. No LLM.

**Example**
```json
// in
{"lot_id": "LOT0007"}
// out
{"lot_id": "LOT0007", "n_die": 5000,
 "params": {"Idd": {"mean": 1.2, "std": 0.04, "min": 1.0, "max": 1.9,
                     "limit": 1.5, "n_breach": 31}}}
```

Implemented: `run.py` (wires `ingest` + `detector.QC_LIMITS`), `verify.py`. Tested
in `tests/test_skills.py`. (`limit` is the per-param USL.)
