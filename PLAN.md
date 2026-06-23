# PLAN — Probe Lot-Disposition Agent (handoff for the implementation session)

> **New session, start here:** read this file, then scaffold the repo (layout + config/env +
> doc stubs) **before** any feature code. All decisions below are frozen unless I say otherwise.
> Companion docs: `KICKOFF.md` (origin + governing prompt), `SETUP.md` (D:\ paths), `PREP_KNOWLEDGE.md`
> (background to know). Stack & hardware are settled; do not re-open them.

## What this is
A **local AI agent for smart manufacturing** that performs **wafer probe lot disposition** —
mirrors the Micron JD line *"perform lot dispositions based on business logic and quality control
standards required by PE and customers."* Runs fully local on Ollama, no cloud.

## Frozen decisions
| Axis | Decision |
|---|---|
| Direction | Probe Lot-Disposition Agent (anomaly-monitoring direction D, specialized) |
| Automation | Detect → draft cited disposition → **human approves/overrides** → commit state + write report |
| Rules | Deterministic **config limits drive detection**; **SOP RAG** supplies the cited rationale |
| Data | **Synthetic** parametric wafer probe data, with injected failure modes → ground-truth labels |
| Agent shape | **Hybrid** — deterministic critical path + an LLM tool-calling Q&A loop over a lot |
| Model | **Qwen2.5-7B-Instruct Q4** for CPU dev; name in config/env, swap up on A6000 |
| UI | **Thin Spring Boot + Thymeleaf** dashboard; ALL agent logic stays in Python |
| Success | **Detection P/R/F1** on labeled lots **+ one scripted end-to-end demo** |
| Thesis | Standalone portfolio piece |
| Skill layer | **Hermes-style file-based skill contract** — each tool = spec + deterministic verifier |
| Memory | **Both** — JSONL/SQLite audit log (source of truth) + a markdown index for demo/teaching |

## Architecture A (approved direction)
Two processes over HTTP:
- **Spring Boot (Java, :8080)** — thin `@Controller` + Thymeleaf. Lot list; flagged lot with drafted
  disposition + cited SOP rule (+ one simple parametric/die-map chart); Approve/Override buttons POST
  to Python. Teaches DI / controllers / templating. **Zero agent logic in Java.**
- **Python agent core (FastAPI, :8000)** — endpoints: `/lots`, `/lot/{id}`, `/disposition/{id}`,
  `/approve`, `/override`, `/ask` (tool-calling loop).

Python internals:
- `ingest.py` — load lot CSV (lot/wafer/die x-y, Vt/Idd/leakage).
- `detector.py` — **DETERMINISTIC**: config test-limits + statistical detector (σ-rule / isolation
  forest) → `flagged` + breached params. *No LLM in the detection decision.*
- `rag.py` — (HW3) ChromaDB over a synthetic `QC-SOP.md`; retrieve the matching clause, cite `[N]`.
- `agent.py` — Qwen2.5 via Ollama: (a) draft rationale **grounded in the retrieved clause**;
  (b) tool-calling loop for `/ask`. Tools come from the skill layer.
- `shell.py` — **DETERMINISTIC** guard: validate (decision, lot) → commit HOLD/RELEASE → write
  report. Never trusts raw LLM output for the action.
- `memory.py` — (HW4) append-only disposition audit log + optional BM25/hybrid recall.
- `skills/` — **Hermes-style** tool contracts (`get_lot_stats`, `retrieve_sop`, `propose_disposition`),
  each a spec + a deterministic verifier.
- `config.py` — `MODEL_NAME` + all `D:\` roots from `.env`. No hardcoded paths.

**Core principle:** classic code *decides and executes*; the LLM only *explains and converses*. This
is what makes a small local 7B safe and useful here.

## Scope
**In:** synthetic data generator (labeled failure modes) · detector · `QC-SOP.md` + RAG · disposition
drafting + report · thin Spring/Thymeleaf dashboard w/ Approve/Override · `/ask` tool-loop ·
Hermes-style skill files · memory (log + index) · eval script printing P/R/F1 · **local-advantage
mock demo** (runs offline / air-gapped, names the advantage at each step) · living docs · seeded &
reproducible.
**Out:** real SECS/GEM or OPC-UA, multi-station scheduling, auth, rich charts beyond one plot, cloud.

## Living knowledge docs (maintain continuously, per KICKOFF #9)
- `docs/HOW_IT_WORKS.md` — high-level: agent loop, tool-calling, RAG, deterministic shell, *why local*.
- `docs/IMPLEMENTATION.md` — technical: modules, Python↔Spring JSON contract, configs, data schema, eval.
- **Rhythm:** build a piece → update both docs → review. Docs never lag the code.

## CPU → GitHub → GPU discipline
- `MODEL_NAME` + `D:\` data/vectorstore/memory roots from `.env` only; no hardcoded paths.
- `.gitignore`: Ollama models, datasets, ChromaDB index, caches, `.env`.
- GPU box: `git pull` → `ollama pull <bigger-model>` → regenerate seeded synthetic data + rebuild index.
- Pinned deps + fixed seeds → CPU and GPU results comparable.

## Suggested first scaffold (no feature code yet)
Repo layout, `.env.example`, `.gitignore`, `requirements.txt`, `config.py`, empty module stubs,
`docs/HOW_IT_WORKS.md` + `docs/IMPLEMENTATION.md` stubs. Then the synthetic data generator first
(everything else depends on having data + labels).

## Fallback (Architecture B)
Same Python core behind **Streamlit** instead of Spring Boot — drop only if CPU-dev time gets tight;
loses the Spring-learning goal. Option: build Python core + Streamlit first, bolt thin Spring on later.

## Open / known risks
- Ollama tool-calling reliability on small models (PREP §1) → validate-then-retry in the shell.
- CPU latency on 7B Q4 is slow → develop against small prompts / a 3B fast model, measure real latency on A6000.
- Synthetic data realism → model credible tool-drift / parametric outliers, or the demo rings false.
