# FAQ & engineering notes

Durable answers to questions raised while building this project. Conceptual
companion to `HOW_IT_WORKS.md`; decisions live in `DESIGN_CHOICES.md`.

## Is `.env` actually necessary?
**Not strictly — but practically yes on Linux/WSL.** `config.py` (pydantic-settings)
has defaults, so the app *runs* without a `.env`. But the path defaults are the
**Windows `D:\` example**; on WSL/Linux those are wrong (they'd create a literal
`D:` folder). So on the GPU box you must set the data roots + `MODEL_NAME` — either
via a `.env` file **or** real environment variables (pydantic-settings reads both).
`.env` is just the convenient way. Tests never need it (they pass dirs explicitly).

## Does the rationale draft come after the detector?
**Yes — it's the last step before the human.** Order:
`ingest → detect (code) → decide (code) → retrieve SOP → draft_rationale (LLM)`.
The detector finds breached params; `decide` maps them to HOLD/RELEASE + clauses;
RAG fetches the clause text; only then does the LLM write the prose, explaining a
decision that is **already made**. The LLM never runs before or instead of detection.

## `draft_rationale` vs `ask` — different LLM structures
- **`draft_rationale`**: single-shot. One prompt (fixed decision + clauses), one
  LLM call, returns a string. No tools, no loop. LLM = pure explainer.
- **`ask`**: the agent loop. A messages list + tool specs; the model may call a
  tool, we run + **verify** it, feed the result back, and loop until a final
  answer or `max_steps`. Returns `AskResult(answer, trace)`. LLM = chooses tools.

## What triggers validate-then-retry in `/ask`? Is the error just passed back?
`_dispatch` **raises** on (a) unknown tool, (b) missing required arg, or (c) the
skill's `verify()` rejecting the output. Any of those → the retry path. We don't
just swallow the error: we append a **corrective** tool message
(`"ERROR: {exc}. Choose a valid tool and arguments."`) so the model sees what went
wrong and tries again, up to `max_retries`, then gives up gracefully. (A richer
corrective could echo the tool schema — easy future improvement.)

## Is there persistent memory?
**Yes.** `memory.py` writes an **append-only JSONL disposition log** to
`MEMORY_DIR` — it persists across sessions, and `recall()` does BM25 over it (plus
`render_markdown_index()`). The `/ask` conversation itself is ephemeral (per call),
which is correct — the durable memory is the audit trail of decisions.

## Is this prompt / harness / loop engineering?
**All three, harness-dominant.**
- **Harness engineering** (core): the deterministic shell, per-tool verifiers,
  `AppContext` DI, validate-then-retry — the scaffolding *around* the model that
  makes a small 7B safe.
- **Loop engineering**: the `/ask` tool-calling loop with step/retry budgets.
- **Prompt engineering**: the decision-fixed rationale prompt, the `/ask` system
  prompt, the corrective retry prompt.

## Is this a real AI-agent build, or just calling Ollama?
Real. It implements a tool-calling agent loop, tool dispatch + verification, RAG
grounding, a deterministic shell, and persistent memory + recall — the
augmented-LLM + harness pattern, not "call model, print output."

## FastAPI vs Flask (why FastAPI)
Concrete wins we *use*: **dependency injection** (the `AppContext` seam that makes
the LLM endpoints hermetically testable), **pydantic** request validation, **auto
OpenAPI docs** for the Spring side, and async/uvicorn. Flask would work but we'd
hand-roll validation, docs, and the test seam.

## ChromaDB vs Ollama (different roles, they cooperate)
- **Ollama** = model runtime: serves the chat LLM *and* the embedding model. Compute.
- **ChromaDB** = vector database: stores clause embeddings + similarity search. Storage.
- Flow: Ollama embeds clauses → ChromaDB stores/searches → retrieved text → Ollama
  chat model generates the grounded answer. Neither replaces the other.

## Did this project need MCP, or only MCP-style tool calls?
The agent only needs **MCP-*style*** tool calls (its own JSON tool schema +
Ollama tool-calling). It does **not** require the MCP protocol to function. The
optional `mcp_server/` exposes the same read-only tools as a **real MCP** server
so external clients (e.g. Claude Desktop) can call them — an integration surface,
not a dependency.

## Our "scheduling" vs ASUS's 排程 (production scheduling)
Two different meanings:
- **Our scheduling** = task/time cadence (cron, autonomous `HEARTBEAT`) — *when the
  agent runs itself*. We deliberately don't (human-triggered).
- **ASUS 排程** = **production scheduling**, an Operations-Research optimization
  (sequence jobs across machines for makespan/throughput/due-dates). A different
  problem; this project does lot *disposition*, not scheduling.

They're **unrelated**, but the *pattern* transfers: agentic scheduling should be
**a deterministic optimizer (OR/predictive model) deciding, the LLM orchestrating
+ explaining** — exactly this project's deterministic-shell design. An auto-approve
toggle (with a confidence gate) could later make this run autonomously, but that's
the deferred autonomy, not OR scheduling.

## Why one agent + tools, not separate agents for ingestion/detection/report?
Those map to existing **deterministic** stages (`ingest.py`, `detector.py`, the
report in `shell.py`) — they should *not* be LLM agents. Detection must be
deterministic (the safety thesis); ingestion is I/O. The only LLM roles are
rationale (draft) and Q&A (`/ask`). More LLM agents = more failure points for a 7B,
no benefit. A `SOUL.md` could set a professional voice, but our **hard boundaries
are enforced in code** (shell + verifiers), which is stronger than prose a weak
model might ignore.
