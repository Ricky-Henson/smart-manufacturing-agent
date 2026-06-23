# Implementation (technical)

> Living doc — never lags the code. Companion to `HOW_IT_WORKS.md`.

## Processes (Architecture A)
Two processes over HTTP:
- **Spring Boot (Java, :8080)** — thin `@Controller` + Thymeleaf. Lot list;
  flagged lot with drafted disposition + cited SOP rule + one chart;
  Approve/Override POST back to Python. **Zero agent logic in Java.**
- **Python agent core (FastAPI, :8000)** — all logic. See `agent_core/`.

## Modules (`agent_core/`)
| Module | Kind | Responsibility |
|---|---|---|
| `config.py` | — | MODEL_NAME + D:\ roots from `.env`. No hardcoded paths. |
| `ingest.py` | I/O | load lot CSV (lot/wafer/die x-y, Vt/Idd/leakage). |
| `detector.py` | **deterministic** | config limits + σ-rule/isolation-forest → flagged + breached params. *No LLM.* |
| `rag.py` | retrieval | ChromaDB over `QC-SOP.md`; cited clause `[N]`. |
| `agent.py` | **LLM** | draft grounded rationale; `/ask` tool-calling loop. |
| `shell.py` | **deterministic** | validate (decision, lot) → commit HOLD/RELEASE → write report. |
| `memory.py` | store | append-only audit log (JSONL/SQLite) + markdown index + recall. |
| `skills/` | contracts | Hermes-style spec + deterministic verifier per tool. |
| `api.py` | HTTP | FastAPI endpoints; thin wiring only. |

## HTTP contract (Python :8000 — Spring calls these)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + active model name |
| GET | `/lots` | lot list + flagged status |
| GET | `/lot/{id}` | one lot's stats + parametric/die-map data |
| GET | `/disposition/{id}` | drafted recommendation + cited rationale |
| POST | `/approve` | commit the drafted disposition (human) |
| POST | `/override` | commit a human override |
| POST | `/ask` | tool-calling Q&A over a lot |

**Wired (DONE).** Each handler delegates to the core; the LLM-touching endpoints
(`/disposition`, `/ask`) and the data/index/memory locations come from an
injectable **`AppContext`** dependency (`get_ctx`) — production = real Ollama +
`.env` roots, tests override with fakes (tmp data + fake index + fake LLMs) so the
suite is hermetic. Errors: unknown lot → 404, failed validation (e.g. blank
approver) → 400. Tested with `TestClient` in `tests/test_api.py`.

## Data schema (synthetic) — DONE
40 lots × 25 wafers of die-level parametrics (`Vt`, `Idd`, `leakage`) on a
circular die map, one CSV per lot + `labels.csv`. Five labeled failure modes
(`idd_shift`, `tool_drift`, `vt_tail`, `edge_leakage`, `none`). Seeded → same
`SEED` gives byte-identical files (test: `tests/test_generate_data.py`). Full
spec: `data_spec/SCHEMA.md`. Generator: `scripts/generate_data.py`
(`python -m scripts.generate_data`).

## Guardrails — where each layer lives in code
(Conceptual version in `HOW_IT_WORKS.md`.) The `SKILL.md` files are **contracts**;
the enforcement is the code below.

| Layer | Enforced by | Mechanism |
|---|---|---|
| Input validation | `api.py`, `shell.py` | lot exists; `decision ∈ {HOLD, RELEASE}` |
| Deterministic decision | `detector.py` | code (limits + σ/iforest) flags; LLM not in the decision |
| Tool-output verification | `skills/*/verify.py` | `verify(inputs, output)` raises on contract violation |
| Grounding / citations | `skills/propose_disposition/verify.py` | `cite_ids ⊆ retrieved ids`; non-empty |
| Human approval gate | `shell.py` | refuses commit without named approver; override needs reason |
| Validate-then-retry | `shell.py` / `agent.py` loop | re-prompt on malformed tool call (small-model reliability) |
| Audit trail | `memory.py` | append-only log of decision + approver, never mutated |

**Contract ↔ enforcement pairing:** for each skill, `SKILL.md` (schema + the
"Verifier" section) is the spec, and `verify.py` is its executable form. They must
stay in sync — changing one without the other is a bug. The verifier never reads
prose (e.g. it does not judge *whether* a rationale is good); it checks
**structure** (enum values, id subsets, ranges), which is what can be made
deterministic.

## Dev environment (WSL)
Develop in **WSL** (mirrors the A6000 GPU box). Debian's Python is
externally-managed (PEP 668), so install into a **venv**, not system Python:
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest          # or: .venv/bin/uvicorn agent_core.api:app
```
`.venv/` is gitignored; the GPU box recreates it from `requirements.txt`.

**Ollama from WSL:** the WSL venv could not reach a Windows-host Ollama at
`localhost:11434` (WSL2 NAT). Since the A6000 box runs Ollama natively in Linux,
install Ollama **inside WSL** (`curl -fsSL https://ollama.com/install.sh | sh`),
point `OLLAMA_MODELS` at a fast disk, and `ollama pull bge-m3`. Until then,
modules that call Ollama (real index build, agent draft) won't run live — but all
logic is unit-tested with injected fakes.

## Config / reproducibility
Pinned `requirements.txt`; all randomness seeded by `SEED`; every path from
`.env`. CPU dev ↔ A6000 GPU comparable. GPU box: `git pull` → `ollama pull` →
regenerate seeded data + rebuild index.

## Detector (DONE) — `detector.py`
Deterministic, no LLM. Config QC limits (`QC_LIMITS`: LSL/USL ~4σ off nominal,
set by PE/customers, separate from the generator's physics) + three explainable
rules per parameter:
1. **out_of_limit** — die fraction outside [LSL, USL] > `MAX_OUT_FRAC` (1%);
2. **mean_shift** — lot mean > `MEAN_SHIFT_SIGMA` (0.75σ) off nominal;
3. **drift** — per-wafer-mean range > `DRIFT_RANGE_SIGMA` (1.5σ).
A param is breached if any rule fires; the lot is flagged if any param is
breached. `detect_lot(df)` is pure/testable; `detect(lot_id)` loads via `ingest`.
Result: `DetectionResult(lot_id, flagged, breached_params, detail)`.

## Eval (DONE) — `scripts/eval.py`
`score()` runs the detector over every labeled lot and returns
**Precision / Recall / F1** of `flagged` vs `is_anomalous`, plus a by-mode
breakdown. On seed 42: **P=0.92 R=0.85 F1=0.88** (tp=22, fp=2, fn=4, tn=14).
Lot-level process variation makes this honest, not a trivial 1.0: the 2 false
positives are healthy lots whose drift trips the Idd mean-shift rule; `tool_drift`
and `vt_tail` are the hard modes (4/6 each). The thresholds favor recall — raising
`MEAN_SHIFT_SIGMA` removes the FPs but drops recall to ~0.69 (the tradeoff).
Reused by `tests/test_detector.py`.
*(Scripted end-to-end demo — still TODO, `scripts/demo_offline.py`.)*

## RAG (DONE) — `rag.py` + `data_spec/QC-SOP.md`
ChromaDB over the SOP; **one clause per chunk** (`_chunks` parses the markdown
into ~12 clauses with source ids like `QC-SOP.md#3.2`). `build_index()` embeds
with `settings.embed_model` (default **bge-m3**) via Ollama and persists to
`settings.vectorstore_dir`; `retrieve(query, k)` returns cited `SopClause`s ranked
by cosine. The embedder is **injectable**, so retrieval is unit-tested with a
deterministic fake — no Ollama needed (`tests/test_rag.py`). CPU dev can set
`EMBED_MODEL=nomic-embed-text` (lighter/faster) with zero code change.

## Disposition decision + agent draft (DONE) — `detector.decide` + `agent.py`
**Decision is code, not LLM (ADR-4).** `detector.decide(DetectionResult) ->
Disposition`: no breach → RELEASE (cite §4.1); any breach → HOLD citing the
governing clause per param (`Vt`→§3.1, `Idd` mean-shift→§3.2 / drift→§3.3,
`leakage`→§3.4); ≥2 breached params → `escalate` + §3.5. Then `agent.draft_rationale(disposition, clauses, llm=)` builds a prompt that **fixes
the decision** and asks the model for a 2-4 sentence rationale grounded only in
the retrieved clauses, cited `[n]`. LLM client injectable → tested offline with a
fake (`tests/test_agent.py`).

## /ask tool-calling loop (DONE) — `agent.ask`
The bounded agent loop (ADR-3). The model is given **read-only** tools
(`get_lot_stats`, `retrieve_sop`; `lot_id` is fixed by the caller, not the model),
picks one, `_dispatch` runs it **and calls its `verify()`** before the result is
trusted, appends the result, and loops until the model returns a final answer or
`max_steps` is hit. A malformed/unknown/failed-verify call triggers
**validate-then-retry** (re-prompt, `max_retries`), then a graceful give-up.
Returns `AskResult(answer, trace)` — the trace is the teaching artifact (which
tools fired, ok/error). Model client injectable → scripted-fake tests
(`tests/test_ask.py`); real Ollama tool-calling via `_ollama_tool_chat`.

## Memory recall (DONE) — `memory.recall` + markdown index
PLAN's "Both": the append-only JSONL log is the source of truth; `recall(query, k)`
runs **BM25** (`rank-bm25`) over a searchable document per record (lot, decision,
clauses, rationale, override reason) and returns top-k records with `_score`
(blank query / empty log → `[]`). `render_markdown_index()` renders the log to a
markdown table for demo/teaching. Fully offline (no Ollama). `tests/test_memory.py`.

## Shell + audit log (DONE) — `shell.py` + `memory.py`
Deterministic guard, no LLM. `shell.commit(lot, decision, approved_by=, rationale=,
clause_refs=)` validates (decision ∈ {HOLD, RELEASE}; **named approver required**,
SOP §5.1), appends to the **append-only JSONL audit log** (`memory.py`, the source
of truth), and writes `memory_dir/reports/<lot>.md`. `approve(disposition, …)`
commits the deterministic recommendation; `override(decision, reason=…)` requires a
reason (§5.2). `state(lot)` = latest log entry. `memory_dir` is injectable →
hermetic tests (`tests/test_shell.py`). `memory.recall` (BM25) is the next memory piece.

## Skills layer (DONE) — `agent_core/skills/`
Three Hermes-style contracts, each a folder with `SKILL.md` (spec) + `run.py`
(deterministic impl) + `verify.py` (deterministic checker, no LLM):
- **get_lot_stats** — per-param stats via `ingest` + `QC_LIMITS`; verify: lot_id
  echoes, `0 <= n_breach <= n_die`, required keys present.
- **retrieve_sop** — delegates to `rag.retrieve`; verify: `len <= k`, cite_ids
  1-based contiguous, non-empty source/text.
- **propose_disposition** — deterministic recommendation (breach→HOLD) +
  `agent.draft_rationale` (injectable LLM); proposal only, never commits; verify:
  recommendation ∈ {HOLD, RELEASE}, cite_ids non-empty ⊆ input ids, breach⇒HOLD.

`run()` produces, `verify()` *proves* (and is shown catching violations).
`tests/test_skills.py` also chains all three end-to-end, each verified.

## Build order (PLAN)
Scaffold (done) → synthetic data generator (done) → detector + eval (done,
F1=0.88 on seed 42) → RAG + `QC-SOP.md` (done) → decide + agent draft (done)
→ shell + report + audit log (done) → skills layer (done) → /ask tool loop (done)
→ memory recall (done) → api wiring (done) → eval credibility (done) →
**Spring UI** (next) → offline demo.
**Core + HTTP surface done; tested offline (41 tests).** What remains is the thin
Spring/Thymeleaf UI + the live demo — no new agent logic.

## Open items
- **Ollama in WSL** — see *Dev environment* above; resolve before the live demo.
- ~~Trivial eval~~ — resolved: process variation + subtler anomalies give F1=0.88
  with a real precision/recall tradeoff (see Eval above).
