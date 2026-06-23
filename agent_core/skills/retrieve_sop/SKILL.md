# Skill: retrieve_sop

**Purpose.** Return the SOP clause(s) that govern a set of breached parameters
or a free-text question, so the agent's rationale is grounded and citable.

**Input**
| field | type | notes |
|---|---|---|
| `query` | string | breached params (e.g. `"Idd over limit"`) or a question |
| `k` | int | optional, default 4 |

**Output**
| field | type | notes |
|---|---|---|
| `clauses` | array | each `{cite_id, source, text}` |

**Verifier (`verify.py`).** Asserts: `len(clauses) <= k`; `cite_id` values are
unique and 1-based contiguous; every clause has non-empty `source` and `text`.
No LLM.

**Example**
```json
// in
{"query": "Idd over limit", "k": 2}
// out
{"clauses": [{"cite_id": 1, "source": "QC-SOP.md#3.2",
              "text": "Lots with >0.5% dies exceeding Idd limit shall be HOLD..."}]}
```

Implemented: `run.py` (delegates to `rag.retrieve`), `verify.py`. Tested in
`tests/test_skills.py`.
