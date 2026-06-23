# How it works (high level)

> Living doc — keep current with the code (PLAN rhythm: build a piece → update
> both docs → review). Plain-language companion to `IMPLEMENTATION.md`.

## What this agent does
A local AI agent that performs **wafer probe lot disposition**: it watches
parametric probe data, **flags** a suspect lot, **drafts a cited HOLD/RELEASE
recommendation**, a **human approves or overrides**, and the decision is
**committed + written to a report**. Everything runs locally on Ollama — no
cloud.

## The big idea: a deterministic shell around a probabilistic core
Classic code **decides and executes**; the LLM only **explains and converses**.
That split is what makes a small local 7B model safe and useful here.

```
 probe data ─▶ detector (deterministic) ─▶ flagged? + breached params
                                              │
                          retrieved SOP clause │ (RAG)
                                              ▼
                     agent/LLM: draft a CITED rationale  ── explanation only
                                              ▼
                     human: Approve / Override  ── the decision
                                              ▼
                     shell (deterministic): validate ─▶ commit HOLD/RELEASE
                                              ▼
                          report + append-only audit log
```

## The pieces (and the concepts they teach)
- **Detector** — statistical thresholds decide anomalies. *Let classic methods
  detect; let the LLM explain.*
- **RAG** — retrieve the governing SOP clause so the rationale is **grounded and
  cited `[N]`**, never invented. (HW3 idea.)
- **Agent loop / tool-calling** — for `/ask`, the LLM observes → picks a tool →
  the tool runs deterministically → result goes back. The *agent* mechanic.
- **Skills** — each tool is a contract with a **deterministic verifier**, so a
  tool result is *proven* to fit its schema before it's trusted.
- **Deterministic shell** — validates and commits the action; never trusts raw
  model output.
- **Memory** — an append-only audit log (source of truth) + a markdown index.

## Guardrails: the md file is the *contract*, the code is the *guard*

A common misread: "are the guardrails just the `SKILL.md` files?" **No.** A
`SKILL.md` only *describes* what must be true (the spec/schema). The guardrail is
the **Python code that enforces it** and refuses to proceed when it isn't. The md
and the code are two halves of one contract:

> `SKILL.md` says *"output must have a `recommendation` of HOLD or RELEASE and a
> non-empty `cite_ids`."* → `verify.py` is the function that actually checks that
> and **raises** if it's violated. The md can't reject anything; the verifier can.

Guardrails here are **layered**, not a single check — each layer assumes the one
before it can fail:

1. **Input validation** — does the lot exist? is the decision one of
   `{HOLD, RELEASE}`? (reject bad requests before anything runs)
2. **Deterministic decision** — the *detector* decides flagged/not, never the LLM.
   The most important guardrail is structural: the model is not in the decision.
3. **Tool-output verification** — every skill result is checked by its `verify.py`
   against the `SKILL.md` contract *before* it's trusted (schema, ranges, ids).
4. **Grounding / citation check** — a drafted rationale must cite clauses that were
   actually retrieved (`cite_ids ⊆ retrieved ids`); no invented citations.
5. **Human approval gate** — `shell.py` will not commit a disposition without a
   named approver; an override must carry a reason.
6. **Validate-then-retry** — small local models emit malformed tool calls; the
   shell re-prompts instead of executing garbage (PREP §1, §3).
7. **Append-only audit log** — accountability is itself a guardrail: every
   decision + who approved it is recorded and never mutated.

The theme is the same as the whole project: **classic code decides and verifies;
the LLM only explains.** That's why a small 7B model is safe here — it is fenced
on every side by deterministic checks.

## Why local wins here (named at each demo step)
Confidential wafer data **never leaves the machine**; it runs **offline /
air-gapped** (demo with the network off); **no per-token cost** on high-volume
parametric streams; full control over the model and the loop.

## TODO (fill as built)
- [ ] Agent loop walkthrough on a real flagged lot.
- [ ] Annotated transcript of one `/ask` tool-calling round.
- [ ] The scripted offline demo, step by step, with the advantage named each step.
