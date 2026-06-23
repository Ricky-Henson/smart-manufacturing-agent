# Skill layer (Hermes-style, file-based contract)

Each tool the agent can call is a **folder** with three files:

| File | Role | LLM? |
|---|---|---|
| `SKILL.md` | The contract: purpose, input schema, output schema, worked example. | — |
| `run.py` | Deterministic implementation invoked by the tool-call. | no |
| `verify.py` | Deterministic verifier: `verify(inputs, output) -> None` (raises on violation). | no |

**Why:** the LLM only *chooses* a tool and *reads* its result. `run.py` produces
the result deterministically and `verify.py` proves it satisfies the contract
*before* `shell.py` trusts it. This is the deterministic shell around the
probabilistic core, applied per tool — the same verifiable-skill pattern as the
Hermes final project.

## Skills (scaffolded)

- `get_lot_stats/` — parametric summary stats for a lot (means, σ, breaches).
- `retrieve_sop/` — cited SOP clause(s) for breached params or a question.
- `propose_disposition/` — assemble a drafted HOLD/RELEASE proposal + citation.
  (Proposal only; the human approves and `shell.py` commits.)

Each is a stub until the underlying modules (`detector`, `rag`) land.
