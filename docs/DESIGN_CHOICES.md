# Design choices & alternatives (ADR-style)

> Living doc. Records *why* the architecture is shaped the way it is, and what it
> would take to change a decision later. Companion to `HOW_IT_WORKS.md` and
> `IMPLEMENTATION.md`.

---

## ADR-1 — Skill layer: Hermes-style verifiable contracts (not persona / agent-OS style)

### In one sentence (plain language)
"**ADR**" = *Architecture Decision Record* — a short note recording one design
decision and why. **ADR-1's decision:** define each tool as a tiny **spec file +
checker script** (Hermes-style), instead of giving the agent a **persona file
set** (`SOUL.md`, `DREAMS.md`, `HEARTBEAT.md`, …). These solve *different*
problems — one makes a **tool** trustworthy, the other gives an **agent** a
personality and the ability to act on its own. So it isn't really "A vs B": we
build the tool contract we need now, and a persona layer can be added later if we
ever want one. **A `SOUL.md` purely for tone/voice is cheap and harmless — that's
fine.** The only thing genuinely out of scope is *autonomy* (see below).

### Goal difference (the core distinction)
They optimize for **different goals**:
- **Hermes' goal = verifiable execution.** Make each *tool* provably do exactly
  what its contract says — correctness, auditability, trust in discrete actions.
  The question it answers: *"did the tool do the right thing, provably?"*
- **Persona/agent-OS ("openclaw") goal = a persistent autonomous self.** Give the
  *agent* identity, values, autonomy, long-horizon goals, and journaling memory —
  a coherent character that runs itself over days. The question it answers:
  *"who is this agent, and how does it act on its own over time?"*

So one is about **trust in what a tool does**; the other is about **the agent's
identity and continuity**. For a regulated, human-approved QC tool, Hermes' goal is
exactly right and the persona goal's *autonomy* is mostly counter to the design
(its *tone* aspect is harmless/optional).

### The two styles are not the same layer
| | **Hermes-style** (chosen) | **Persona / agent-OS style** (e.g. `SOUL.md`, `DREAMS.md`, `HEARTBEAT.md`) |
|---|---|---|
| Governs | how a single **tool** is defined + trusted | how the **agent** is framed + how it runs |
| Unit | one tool = `SKILL.md` spec + `run.py` + deterministic `verify.py` | one agent = identity + autonomy + journaling files |
| Concern | **verifiable execution** | **personality + autonomous behavior** |
| Trust model | output is *proven* against a schema before the shell trusts it | the agent self-directs and acts on a cadence |

They are **orthogonal**: Hermes is about *tools*, persona-style is about the
*agent's self*. One is not a replacement for the other.

### Why Hermes-style fits THIS project
This is an **industrial QC disposition tool**, not a companion agent:
- **Human-in-the-loop by design** — a person approves/overrides every HOLD/RELEASE.
  An agent that acts on its own cadence (`HEARTBEAT.md`) or pursues self-directed
  goals (`DREAMS.md`) is the *opposite* of what we want.
- **Auditable + deterministic** — disposition is a regulated decision. Every tool
  result must be schema-verified (`verify.py`) before `shell.py` commits it. The
  deterministic shell around a probabilistic core *is* the safety story.
- **Tone is free; autonomy is the real concern.** A `SOUL.md` that only sets the
  *voice/tone* of the drafted rationale is harmless and optional — add it if you
  like. What's genuinely out of scope is **autonomy**: `HEARTBEAT.md` (acting on a
  schedule) and `DREAMS.md` (self-directed goals) contradict "a human approves
  every disposition," and unattended action in a regulated QC decision needs new
  guardrails first.
- **Continuity with your prior work** — same verifiable-skill pattern as the
  Hermes final project; the verifier *proves* the contract rather than trusting prose.

### Which persona concepts still map (so a future switch is graceful)
| Persona file | Analog in this project | Status |
|---|---|---|
| `IDENTITY.md` | `config.py` (model/role) + a short identity note | partial |
| `USER.md` | operator/approver context | implicit (single operator) |
| `AGENTS.md` (operating rules) | the deterministic shell rules + this ADR | covered |
| `TOOLS.md` | `agent_core/skills/` (Hermes contracts) | covered |
| `MEMORY.md` | `memory.py` — audit log (truth) + markdown index | planned |
| `BOOT.md` / `BOOTSTRAP.md` | `scripts/build_index.py`, `generate_data.py` setup | planned |
| `SOUL.md` | optional — could set the *tone* of the drafted rationale | optional (tone only) |
| `HEARTBEAT.md` | — *(omitted: human approves; no autonomous cadence)* | out of scope |
| `DREAMS.md` | — *(omitted: no self-directed goals)* | out of scope |

### Can we adopt persona / agent-OS style later? — Yes, additively.
Because the two styles are orthogonal layers, a persona layer can sit **on top of**
the Hermes verifiers without removing them:
1. Add agent-framing files (`IDENTITY.md`, `AGENTS.md`, and a memory index) as a
   thin layer that *describes* the agent — the tools underneath stay Hermes
   contracts with deterministic verifiers.
2. Keep `verify.py` as the trust boundary regardless of how the agent is framed.
3. Only introduce autonomy files (`HEARTBEAT.md`/`DREAMS.md`) if the product goal
   ever changes from "human-approved disposition" to "autonomous monitoring" — that
   is a **product** decision, not just a file-format one, and would need new
   guardrails before any unattended action is allowed.

**Bottom line:** Hermes-style is the right tool contract for a safety-critical,
human-approved industrial task. Persona/agent-OS style is a different (optional)
layer we can add later without throwing away the verifiers — but its autonomy
pieces are intentionally out of scope for a disposition tool.

---

## ADR-2 — Coverage of the agent component domains

A useful checklist frames agent-building as components across several domains:
**models · tools · knowledge & memory · audio & speech · guardrails ·
orchestration.** Where this project stands:

| Domain | This project | Where | Status |
|---|---|---|---|
| **Models** | Qwen2.5 via Ollama; name + host from `.env`; swap up on the A6000 | `config.py`, `agent.py` | scaffolded |
| **Tools** | Hermes skill contracts (`get_lot_stats`, `retrieve_sop`, `propose_disposition`) + tool-calling loop | `skills/`, `agent.py` | scaffolded |
| **Knowledge** | RAG over `QC-SOP.md` (ChromaDB), cited `[N]` | `rag.py`, `data_spec/QC-SOP.md` | scaffolded |
| **Memory** | append-only audit log (truth) + markdown index; optional BM25/hybrid recall | `memory.py` | scaffolded |
| **Guardrails** | the **deterministic shell**: validate (decision, lot) → commit; per-tool `verify.py`; detector decides, LLM never does; validate-then-retry on flaky tool calls | `shell.py`, `skills/*/verify.py`, `detector.py` | scaffolded (core differentiator) |
| **Orchestration** | hybrid: deterministic critical path + LLM tool-calling Q&A loop; two-process HTTP (FastAPI ↔ Spring) | `api.py`, `agent.py`, `ui-springboot/` | scaffolded |
| **Audio & speech** | — | — | **out of scope** (text + web UI only; no voice in a disposition tool) |

So: every domain that matters for this task is **planned and scaffolded**, with
**guardrails** as the deliberate strength. **Audio & speech is intentionally
excluded** — it adds nothing to a wafer-disposition workflow.

---

## ADR-3 — Which agent workflow pattern is this?

A common taxonomy (from "building effective agents") separates **workflows**
(LLM steps wired by fixed code) from **autonomous agents** (the LLM directs its
own steps). The building block underneath both is the **augmented LLM** = an LLM
plus retrieval + tools. The named workflow patterns are: **prompt chaining,
routing, parallelization (sectioning / voting), orchestrator-workers,
evaluator-optimizer.** This project uses **two** of them, deliberately the
simplest that fit:

### 1. Disposition critical path = a deterministic workflow (prompt-chaining shape) with a human gate
```
ingest ─▶ detect (CODE) ─▶ retrieve SOP (RAG) ─▶ draft rationale (ONE LLM call)
                                                        ─▶ HUMAN approve/override (gate) ─▶ commit
```
It's a **fixed pipeline where all links but one are deterministic code**, and the
single LLM call is *augmented* by retrieval. Closest named pattern: **prompt
chaining with a gate** — except the chain is driven by code, not by the model
choosing the next step. The model is **not** in the disposition decision.

### 2. `/ask` = a tool-calling agent loop — but **bounded**, not autonomous
The LLM observes → picks a tool → reads the (verified) result → iterates. That's
the **agent** pattern. It is *agent-shaped* but **not autonomous in authority**:
read-only tools, `verify.py`-gated outputs, no unattended actions, and a human
approves any disposition.

### What this is NOT (and the natural place each could enter later)
| Pattern | Used? | If we ever add it |
|---|---|---|
| Routing | no | route a flagged lot by `failure_mode` to a specialized handler |
| Parallelization (sectioning) | no | analyze wafers/params in parallel for speed |
| Parallelization (voting) | no | a **detector ensemble** voting on flagged/not |
| Orchestrator-workers | no | only if tasks need dynamic decomposition (they don't) |
| Evaluator-optimizer | no | a 2nd pass that checks the rationale cites the right clause, then re-drafts |
| Fully autonomous | **no, by design** | would require new guardrails before any unattended action |

**Principle:** use the **simplest pattern that works**; add agentic complexity
only when it demonstrably improves the outcome. A deterministic workflow plus one
bounded agent loop is the right altitude for a safety-critical disposition tool.

---

## Scope FAQ (things deliberately NOT in this project)

| Question | Answer | Why / future path |
|---|---|---|
| **Scheduling / autonomous cadence?** | **No.** | Human-triggered, not time-triggered — the disposition runs when a person reviews lots; the detector runs on-demand. Same reason `HEARTBEAT.md` is out (ADR-1) and PLAN lists "multi-station scheduling" as out of scope. Could later add a polling/monitoring loop (the original "direction D"), but it would need guardrails before any unattended action. |
| **Multi-agent?** | **No.** | One hybrid agent: a deterministic critical path + one bounded tool-calling loop. "Orchestrator-workers" (ADR-3) is unused — a narrow disposition task doesn't need coordinating agents, and more agents = more places a small local model can fail. Future-optional only. |
| **Different agent *tuned* per task?** | **No.** | We specialize by **tools + prompts**, not by separate tuned models. The detector is already a specialized *non-LLM* component; "draft rationale" and "/ask" share one model with different prompts/tools. Per-task fine-tuned models add training data, infra, and drift for no benefit on one local 7B — over-engineering. |
| **LangChain / agent framework?** | **No.** | LangChain / LlamaIndex / CrewAI provide the same building blocks (agent loop, RAG, tool-calling, memory); we **hand-roll** them (PREP §2) for clarity, verifiability, and control — owning the loop makes the deterministic shell straightforward. Concepts transfer; no dependency. Could adopt later. |
| **Audio / speech?** | **No.** | Text + thin web UI; voice adds nothing to wafer disposition (ADR-2). |
| **Cloud / external LLM?** | **No.** | Fully local on Ollama by hard constraint — that *is* the project's thesis (data never leaves the machine, offline, no per-token cost). |

---

## ADR-4 — Who decides HOLD/RELEASE: code, from the SOP rule

**Decision.** The disposition recommendation is computed **deterministically** —
the breached rule(s) → the governing SOP clause → HOLD/RELEASE. The LLM does
**not** decide; it only drafts the *cited rationale*, and `shell.py` commits after
human approval.

**Why.** It's the core principle (classic code decides, LLM explains) applied to
the single most important output. The SOP (`data_spec/QC-SOP.md`) already encodes
an explicit HOLD/RELEASE action per breach, so the disposition is a **lookup, not
a judgment** — fully auditable (traceable to a clause, not to model prose) and
safe on a small local model.

**Alternative considered:** *LLM proposes, shell validates.* Rejected for the
critical path (less deterministic), but the same **validate-then-retry** guard
still wraps any tool call the LLM makes in `/ask`.

**Embedding choice (related, ADR-2 domain "knowledge").** Default
`EMBED_MODEL=bge-m3` (matches the A6000 target); CPU dev may swap to
`nomic-embed-text` via `.env` with zero code change. At ~12 SOP clauses, embedding
quality is not the bottleneck, so this is a config knob, not an architecture fork.
