# Probe Lot-Disposition Agent

A **local** AI agent for smart manufacturing that performs **wafer probe lot
disposition**: detect a suspect lot → draft a **cited** HOLD/RELEASE
recommendation → **human approves/overrides** → commit state + write a report.
Runs fully on **Ollama, no cloud**.

**Core principle:** classic code *decides and executes*; the LLM only *explains
and converses* — a deterministic shell around a probabilistic core.

## Status
**Python core + HTTP surface complete; 41 tests green (all offline).** Done:
synthetic data generator (subtle anomalies + lot-level process variation) ·
deterministic detector + eval (**F1=0.88** on seed 42, a real precision/recall
tradeoff) · RAG over `QC-SOP.md` · deterministic disposition (`decide`) + LLM
rationale draft · deterministic shell + append-only audit log · Hermes-style
skills (run + verify) · bounded `/ask` tool loop · BM25 memory recall · FastAPI
endpoints. **Remaining (integration only):** thin Spring/Thymeleaf UI · scripted
offline demo. Both need **Ollama running in WSL** (see below).

Build order + per-module status: [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md).
Concepts: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md). Decisions/ADRs:
[docs/DESIGN_CHOICES.md](docs/DESIGN_CHOICES.md). Frozen direction: [PLAN.md](PLAN.md).

### Resuming in a new session (e.g. after `git pull` on the GPU box)
1. `python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt`
2. `.venv/bin/python -m pytest` — expect 41 passing, no Ollama needed.
3. Install Ollama in WSL + `ollama pull bge-m3` (and a chat model for `MODEL_NAME`);
   `cp .env.example .env` and set Linux paths (`/mnt/d/...`).
4. `python -m scripts.generate_data` → `python -m scripts.build_index` → run the API.
5. Next implementation step: the Spring UI, then `scripts/demo_offline.py`.

## Layout
```
agent_core/      Python agent core (FastAPI :8000) — all logic here
  config.py      MODEL_NAME + D:\ roots from .env (no hardcoded paths)
  ingest.py      load lot CSV
  detector.py    DETERMINISTIC anomaly detection (no LLM)
  rag.py         ChromaDB SOP retrieval, cited [N]
  agent.py       Qwen2.5 via Ollama: draft rationale + /ask tool loop
  shell.py       DETERMINISTIC guard: validate -> commit -> report
  memory.py      append-only audit log + markdown index + recall
  api.py         HTTP endpoints (thin wiring)
  skills/        Hermes-style tool contracts (spec + deterministic verifier)
scripts/         data generator, index build, eval (P/R/F1), offline demo
data_spec/       QC-SOP.md source + synthetic-data schema notes
docs/            HOW_IT_WORKS.md (concepts) + IMPLEMENTATION.md (technical)
                 + DESIGN_CHOICES.md (why Hermes-style; domain coverage)
ui-springboot/   thin Spring Boot + Thymeleaf dashboard (:8080) — see NOTES.md
tests/           pytest
```
Heavy, regenerable artifacts (datasets, vector store, memory, models) live on
`D:\` per [SETUP.md](SETUP.md) — never committed.

## Quick start (WSL — mirrors the GPU box)
Debian Python is externally-managed (PEP 668), so always use a venv:
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env            # then edit paths/model
.venv/bin/python -m pytest
.venv/bin/uvicorn agent_core.api:app --port 8000
```

## CPU now → GPU later
Develop on CPU with a small model; push to GitHub; on the A6000 `git pull` →
`ollama pull <bigger model>` → regenerate seeded data + rebuild index. Only
`MODEL_NAME` changes (in `.env`).
