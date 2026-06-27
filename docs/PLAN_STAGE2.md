# PLAN — Stage 2: from a lot-disposition agent to a Detect → Act → Optimize MES

> Companion to `PLAN.md` (Stage 1, frozen). Stage 1 = the **probe lot-disposition
> agent** (built, 43 tests). This plans the expansion toward the fuller
> Detect → Act → Optimize vision. **Do Stage-1 remaining work (Spring UI + offline
> demo) first; Stage 2 is GPU-side.**

## The key reframe: the vision blends TWO MES domains
| Domain | What it is | In this project |
|---|---|---|
| **A. Wafer QC / lot disposition** (Micron-style) | parametric wafer data → flag → Hold Lot → cited report | **Stage 1 — built** |
| **B. Equipment health + production scheduling** (ASUS-style) | machine sensor (pressure) time-series → predictive maintenance → halt machine → **OR-Tools** re-route jobs | **Stage 2 — new** |

The "pressure / halt the machine / OR-Tools re-route" lines are **domain B**; the
"wafer test data / Hold Lot / RCA report" lines are **domain A**. They're both MES,
but distinct subsystems. Stage 1 is A; Stage 2 adds B and makes the loop
autonomous + optimizing.

## Gap analysis (vision line → status → verdict)
| Vision step | Status now | Should we? |
|---|---|---|
| Generate synthetic parametric wafer data (V, I, x-y die) | **DONE** (`generate_data.py`) | ✅ keep; scale up on GPU |
| Time-series **forecasting** model for subtle drift / yield drop | **PARTIAL** — we detect drift *reactively* (rules), no *trained forecaster* | ✅ Stage 2 (predictive) |
| TS model predicts anomaly → triggers agent | **PARTIAL** — detector triggers flow, but reactive not predictive | ✅ Stage 2 |
| Detect a **pressure anomaly on a machine**, alert agent | **NOT DONE** (we monitor wafer params, not machine sensors) | ✅ Stage 2 (domain B) |
| **Act: auto-halt machine** + log "maintenance required" | **NOT DONE** (no machine control; human-approved) | ⚠️ Stage 2, **gated** |
| **Auto-execute Hold Lot** in DB | **PARTIAL** — HOLD is *computed* by rules + *human-approved*, logged to JSONL (not a DB) | ⚠️ Stage 2, **gated** |
| Auto-generate **root-cause hypothesis report** | **DONE-ish** — cited SOP rationale + report (frame as RCA hypothesis) | ✅ minor polish |
| **Optimize: OR-Tools re-route pending jobs** | **NOT DONE / NOT PLANNED** | ✅ Stage 2 (the ASUS 排程 piece) |

**Bottom line:** Stage 1 covers Detect (reactive) + a human-gated "Act" (Hold) +
the RCA-style report. **Predictive detection, autonomous Act, equipment health, and
Optimize (scheduling) are Stage 2.**

## What SHOULD be done (Stage 2 roadmap, phased)
**Phase 2.0 — bridge seams (cheap, in Stage 1 so Stage 2 bolts on)**
- **Detection confidence/severity score** — *(added now)* `DetectionResult.severity`
  = how far past the worst threshold. Enables the auto-hold gate + UI risk sorting.
- **Disposition policy seam** — a pure function `policy(disposition, severity)` →
  {auto-commit | needs-human}. Default = needs-human (Stage 1 safety preserved).
- **Event/trigger interface** — a thin "on_flagged(lot)" hook so a stream/forecaster
  can drive the pipeline (today it's request-driven).

**Phase 2.1 — Predictive detection (domain A, forecasting)**
- Train a TS forecaster (e.g. statsmodels/sktime; ARIMA or a small model) on the
  per-wafer parametric sequence to **predict impending drift** before a lot fully
  breaches. Keep the **decision deterministic** — the forecaster raises a flag,
  classic rules + the policy decide.

**Phase 2.2 — Gated autonomy (Act)**
- **Auto-HOLD on high confidence** (HOLD is *fail-safe* — quarantining is low-risk).
  **RELEASE and borderline always go to a human.** This answers "auto-hold?": yes,
  but asymmetric + confidence-gated, with the full audit trail. Add an `AUTO_HOLD`
  policy flag (default off).

**Phase 2.3 — Optimize: production scheduling (domain B, the ASUS 排程 piece)**
- Add an **OR-Tools (CP-SAT)** scheduler: given pending jobs + machine availability,
  when a lot is HELD or a machine is down, **re-route/re-sequence** to optimize
  makespan / throughput. **Deterministic optimizer decides; the LLM explains** the
  new schedule (same deterministic-shell pattern — the LLM does NOT compute the
  schedule). This is exactly how ASUS's "Agentic AI + OR for 排程" is built.

**Phase 2.4 — Equipment health (domain B)**
- A synthetic **machine sensor stream** (pressure/temp) + predictive-maintenance
  trigger + a (simulated, logged) **halt-machine** command. Feeds Phase 2.3.

## What should NOT be done (scope guards)
- **Don't make detection or scheduling an LLM.** Classic models decide; the LLM
  explains. (Detection = rules/forecaster; scheduling = OR-Tools.)
- **No full autonomy without the confidence gate + audit.** RELEASE stays human.
- **Stay local/offline.** No cloud OR/ML services — the thesis is local.
- **Don't build OR-Tools before the Stage-1 demo works.** Finish A first.
- **Don't add a heavy DB yet.** The JSONL audit log is fine; "DB" can be SQLite later.

## Architecture seams (so Stage 1 doesn't need a rewrite)
1. **Severity/confidence** on detection — *added now*.
2. **Policy layer** between `decide` and `shell.commit` (auto vs human).
3. **A `Job` / `Machine` model + a `scheduler` module** (Stage 2.3) consuming
   disposition + equipment events. Keep it a separate package (`scheduler/`), like
   `mcp_server/`, so it's optional and independently testable.
4. **Keep the deterministic shell everywhere** — OR-Tools and the forecaster are
   new *deterministic cores*; the LLM remains the explainer.

## Dependencies to add (Stage 2, not now)
- `ortools` (CP-SAT scheduler), a TS lib (`statsmodels` or `sktime`). Keep them in
  a `requirements-stage2.txt`, optional like `requirements-mcp.txt`.

## Sequencing vs the GPU move
1. **Now / Stage 1.5:** severity score (done), this plan. *(optional: policy seam)*
2. **Finish Stage 1:** Spring UI + offline demo (needs JDK/Maven + live Ollama).
3. **On GPU (Stage 2):** forecaster → gated autonomy → OR-Tools optimize → equipment.

## Open questions for ricky (decide before Phase 2.3)
- Is the **OR-Tools scheduling** in scope for *this* project, or a separate repo? It
  is a large, somewhat independent subsystem (domain B).
- Auto-HOLD: comfortable with asymmetric autonomy (auto-HOLD, human-RELEASE)?
- Is a real **DB** (SQLite) wanted, or is the JSONL log enough for the demo?
