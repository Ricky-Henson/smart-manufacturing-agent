# Smart-Manufacturing Local AI Agent — project kickoff

> **How to use this file:** open this **project folder** in Claude Code (your config dir should be
> `ricky-claude` so your skills + memory load — one-time setup is in the chat). The project lives
> **here**, in `...\GenAI\smart-manufacturing-agent` — *not* inside the `ricky-claude` config
> folder. Then copy the prompt block below as your first message in a new session. It tells Claude
> to run a Q&A to fix the direction *before* building anything.

---

## Prompt to paste (copy everything between the lines)

---
I'm starting a small personal project: a **local AI agent for 智慧製造 (smart manufacturing)**,
centered on **automation** — smart manufacturing is usually about automating *something*, and a big
part of this discussion is deciding *what* to automate and *how*. This is my own project (not
coursework), and it lives in this folder. **Hard constraints: it runs locally on Ollama, no cloud;
and Ollama's models plus all data/memory live on the `D:\` drive (my `C:\` is limited — see
`SETUP.md`).** **Stack is decided: hybrid** — a Python agent core (reusing my HW patterns) + a thin
**Spring Boot** web front-end that calls it over HTTP (Spring Boot is new for me; I want to learn its
core). **Dev/test:** I develop on **CPU** now and test later on a remote **NVIDIA RTX A6000 (~48 GB
VRAM)** by pushing to GitHub and pulling on the GPU box — so keep the model name configurable, store
models/data on `D:\`, gitignore models/data, and use no hardcoded paths (see `PREP_KNOWLEDGE.md` §8).

Background you can assume about me (my skills and memory should auto-load): in HW4 I built a
cross-session memory layer for a local coding agent (Pi + Ollama) with BM25/hybrid retrieval; HW3
was a personal RAG; HW2 was a spec-driven CLI; the final project was verifiable Hermes Agent
skills. I work in the "deterministic shell around a probabilistic core" style, value clean
reproducible code, and verify before claiming something is done.

**Do NOT start building or writing code yet.** First, run a focused **Q&A to fix the direction**
with me (use the question UI, a few questions at a time, let me steer). I have two candidate
directions in mind, but they still need discussion and I want you to **propose better ones too**:

- **(A) A local "Claude-style" agent that does a task the smart-manufacturing industry needs** — an
  autonomous, tool-using agent on a local Ollama model that can read data/manuals, reason, and
  recommend or take an action. The automation = automating that industry task.
- **(B) A local Q&A assistant for smart manufacturing** — answers manufacturing questions grounded
  in a local knowledge base (SOPs / manuals / specs) with citations (RAG).

Stronger candidates you should weigh and refine with me (and add your own better ideas):

- **(C) Maintenance / troubleshooting agent** — operator describes a symptom; the agent diagnoses
  from equipment logs + manuals (RAG), cites sources, recommends a fix, and can auto-generate a
  work order or report. (RAG + tool-use + a concrete automation.)
- **(D) Anomaly-monitoring agent** — watches a replayed sensor stream, flags + explains anomalies in
  plain language, and triggers an alert / summary report. (Time-series + LLM explanation +
  automated first-line monitoring.)
- **(E) SOP / operator copilot** — walks an operator through a procedure step by step, answers
  questions inline, and logs completion for compliance. (Guided automation + record-keeping.)

In the Q&A, help me decide across these (or a better idea you propose), and nail down:

1. **Which direction**, and *what specifically gets automated* (the decision / task / monitoring job
   / report / workflow).
2. **Agent shape** — what makes it an agent (tool-calling, monitoring loop, RAG assistant, analysis
   pipeline, control-advisory) and which tools/actions it needs.
3. **Data** — what I have or can simulate, local only: sensor time-series, equipment / MES / SCADA
   logs, manuals / PDFs, images, CSV, or synthetic.
4. **Ollama / models** — pick a model for **CPU dev now** (a small quantized model, e.g. 3B–8B) and
   note I'll test on the **A6000 (~48 GB)** later via GitHub push/pull (can run a larger model
   there); keep the model name configurable. Fully offline; models on `D:\`.
5. **Interface (decided: hybrid — confirm the details):** a Python agent core exposed as a small
   local HTTP service (FastAPI/Flask) + a thin **Spring Boot** web UI calling it. In the discussion,
   confirm how thin the Spring Boot layer stays and what the demo UI actually shows. (Spring Boot =
   a localhost web UI, not a desktop GUI.)
6. **Scope & success** — the minimal viable demo for a small project, and how I'll judge it works (a
   metric, a dataset, or a concrete demo scenario).
7. **Thesis link** — whether this should connect to my thesis or stay standalone.
8. **Local-agent advantage mock case** — include a concrete, scripted mock scenario whose *point*
   is to show **why a local AI agent wins here** (not just that the agent runs): confidential wafer
   data never leaves the machine, it works **offline / air-gapped**, no per-token cloud cost on
   high-throughput streams, and full control over model + loop. The end-to-end demo must make these
   advantages visible (e.g. run it with the network off) and a short note should name the advantage
   at each step.
9. **Living knowledge docs (teach-as-you-build)** — maintain running documentation that I can learn
   from, updated continuously as the project grows, at **two levels**: (a) a **high-level** "how the
   AI agent works" explanation (the agent loop, tool-calling, RAG, the deterministic shell — in
   plain language), and (b) a **detailed technical** explanation of the actual implementation
   (each module, the HTTP contract, configs, the data schema, the eval method). The goal is that by
   the end I understand both *how AI agents work conceptually* and *exactly how this one is built*.

After the Q&A, **propose 1–2 concrete architectures** (components + how my existing patterns and
skills — HW4 memory, HW3 RAG, the deterministic-shell design, the spec-driven CLI / Streamlit GUI
patterns — slot in, all on Ollama), and **wait for my approval before any implementation.**
---
