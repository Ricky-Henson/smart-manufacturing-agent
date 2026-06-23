# Skill: propose_disposition

**Purpose.** Assemble a *drafted* disposition for a flagged lot: a HOLD/RELEASE
recommendation, the breached parameters, and the SOP citation backing it. This
is a **proposal only** — the human approves/overrides and `shell.py` commits.

**Input**
| field | type | notes |
|---|---|---|
| `lot_id` | string | a flagged lot |
| `breached_params` | array | from `detector.py` |
| `clauses` | array | from `retrieve_sop` |

**Output**
| field | type | notes |
|---|---|---|
| `lot_id` | string | echoes input |
| `recommendation` | enum | `"HOLD"` or `"RELEASE"` |
| `breached_params` | array | echoes input |
| `cite_ids` | array | the `[N]` clauses the rationale relies on |
| `rationale` | string | grounded; every claim traceable to a cite_id |

**Verifier (`verify.py`).** Asserts: `recommendation in {HOLD, RELEASE}`;
`cite_ids` is non-empty and a subset of the input clause ids; if
`breached_params` is non-empty the recommendation is `HOLD`. No LLM — the
verifier never reads the rationale's *prose*, only its structural contract.

Implemented: `run.py` (deterministic recommendation + `agent.draft_rationale`),
`verify.py`. Proposal only — never commits. Tested in `tests/test_skills.py`.
