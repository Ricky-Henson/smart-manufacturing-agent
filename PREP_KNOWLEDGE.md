# Prep knowledge — local AI agent for smart manufacturing

High-level only. Dig into details yourself; this is the map of what to know before/while building.
"You already know this" = covered by your HW1–HW4 / final-project experience.

## 1. Local LLM serving with Ollama
- How Ollama runs models: `ollama pull/run`, the local HTTP API (OpenAI-compatible
  `/v1/chat/completions`), model tags, GGUF format, **quantization** (Q4/Q5/Q8 — quality vs size).
- **Hardware reality:** VRAM/RAM limits model size; CPU vs GPU inference; tokens/sec; the model's
  **context window** caps how much you can feed it. Pick a model that fits your machine.
- **Tool-calling support varies by model** — this is the single biggest gotcha (you saw it: gemma4
  emitted broken tool-call tokens). Check which local models reliably do function/tool calling
  (e.g. recent Qwen2.5, Llama 3.x families); small models are flaky.

## 2. Agent fundamentals
- What makes it an *agent* vs a script: an **LLM + tools + a loop** (observe → decide → act →
  observe). Know the **ReAct / tool-calling loop** pattern and basic planning.
- **Function / tool calling:** defining a tool's JSON schema, parsing the model's chosen call,
  executing it deterministically, feeding the result back. This is the core mechanic.
- **Deterministic shell around the probabilistic core** (you already know this): wrap the LLM in
  code that validates, executes, and verifies — never trust raw model output for actions.
- **Memory** (you already have the HW4 patterns): short-term (the context window) vs long-term
  (retrieval from a store); when to persist; BM25/hybrid retrieval.
- **Frameworks vs from-scratch:** LangChain / LlamaIndex / AutoGen / CrewAI exist, but for a small
  local project a minimal hand-rolled loop is usually clearer and easier to verify.

## 3. Structured-output reliability on small local models
- Small models are unreliable at JSON / tool calls. Know the mitigations: **JSON / grammar-
  constrained decoding**, explicit prompt discipline (you learned: weak models skim — front-load
  the mandatory step), and **validate-then-retry** in the deterministic shell.

## 4. Retrieval / RAG — only if the agent answers questions or uses manuals
- Chunking + overlap, a **local embedding model** (e.g. bge-m3), a local vector DB (ChromaDB),
  top-k retrieval, and **grounded, cited** generation ("answer only from context, cite `[N]`, say
  insufficient info"). You already have all of this from HW3.

## 5. Smart-manufacturing domain (the part that's new for you)
- **Industry 4.0 / smart manufacturing** basics: what problems it cares about — **predictive
  maintenance, quality / defect inspection, anomaly & fault detection, OEE, scheduling**.
- **Data sources & types:** sensor/IoT **time-series**, equipment **logs**, **MES** (manufacturing
  execution system) and **SCADA** data, **PLC** signals, manuals/SOPs (PDF), images.
- **Connectivity protocols** (high level, only if touching real equipment): **OPC-UA, MQTT,
  Modbus** — how machines expose data. For a prototype you'll **simulate / replay** instead.
- **Public datasets to prototype with** (search these): NASA C-MAPSS turbofan & bearing datasets
  (predictive maintenance), industrial anomaly / surface-defect datasets (e.g. MVTec-style), and
  generic time-series anomaly benchmarks.

## 6. Light ML for the chosen task (depends on direction)
- If anomaly / predictive: **time-series windowing + features**, simple detectors (statistical
  thresholds, isolation forest, etc.) — let classic methods *detect*, let the LLM *explain/decide*.
- Evaluation: **precision / recall / F1** for detection (and you already know Recall@k / MRR /
  nDCG for retrieval).

## 7. App & engineering — DECIDED: hybrid (Python agent + Spring Boot web front-end)
A **Python agent core** (reusing your HW3 RAG / HW4 memory / deterministic-shell patterns, driving
Ollama) exposed as a small local HTTP service (FastAPI/Flask), with a **Spring Boot** web app as the
front-end that calls it over HTTP. You learn Spring Boot without throwing away your Python.

**What you actually need to learn (the core):** Java + Maven/Gradle basics; Spring Boot fundamentals
— project layout, `@RestController` / `@Controller`, **dependency injection (IoC)**,
`application.yml` config, the embedded Tomcat server; **Thymeleaf** (server-rendered pages) or a
simple REST + static frontend; and making HTTP calls from Spring to your Python service. (Spring AI
/ Ollama-in-Java is *not* needed in the hybrid — Ollama is driven from Python — so skip it unless you
later move logic into Java.)

**Why Spring Boot dominates enterprise (learning context).** In the thin hybrid front-end you
*won't* exercise most of this, but it's *why* Spring is worth knowing, and why it's relevant to
manufacturing/enterprise (智慧製造) backends:
- **Dependency injection / IoC container** — Spring constructs and wires your objects for you, giving
  loose coupling and easy testing/mocking. This is the heart of Spring and of large, maintainable
  codebases.
- **Auto-configuration + starters** — sensible defaults and one-line dependencies stand up a
  production-grade app fast (embedded server, DB, security) — "convention over configuration."
- **Huge mature ecosystem** — Spring Data (databases/JPA), Spring Security (auth/SSO/LDAP), Spring
  MVC/WebFlux, Spring Cloud (microservices), Spring Batch (bulk jobs), messaging (Kafka/RabbitMQ).
  Enterprises get most cross-cutting needs off the shelf instead of building them.
- **Production-readiness / ops** — Actuator (health checks, metrics), externalized config + profiles,
  structured logging, single-jar packaging, observability — built to run reliably at scale.
- **JVM + stability + governance** — Java's type safety, performance, and a large tooling/talent
  pool; long-term support and strong backward-compatibility that risk-averse enterprises (incl.
  manufacturing MES / ERP / industrial-IoT backends) depend on. That's why Java/Spring is everywhere
  in industry.

It's fine **not** to implement those heavy capabilities here — the thin front-end still teaches you
the foundation (structure, DI, controllers, templating, calling a service), which is what everything
else builds on.

**Offline & reproducible:** everything local (Ollama + local data), pinned deps, a clean project
layout, and tests — your usual standard.

## 8. Dev/test workflow — CPU now, GPU (A6000) later via GitHub
- **Where you run:** develop locally on **CPU** for now; test on a remote **NVIDIA RTX A6000
  (~48 GB VRAM)** reached by pushing to a GitHub repo and pulling on the GPU box, then continue
  implementing if needed.
- **Model follows the machine:** on CPU use a **small quantized model** (e.g. a 3B–8B at Q4) — slow
  but fine for wiring/logic; on the A6000 you can run a much larger model comfortably. Keep the
  **model name in config/env**, never hardcoded, so you swap CPU↔GPU models with zero code change
  (you already design model-agnostic).
- **Push code, not data:** **gitignore** the Ollama models, datasets, vector store, and caches (all
  on `D:\`). The GPU box pulls the *code* and re-pulls models via `ollama pull` + rebuilds any index
  — never commit GBs.
- **Path portability:** the GPU box has different drives/paths, so read every data path from
  config/env — **no absolute paths in committed source** (your usual rule). This is what makes the
  CPU → GitHub → GPU round-trip painless.
- **Determinism across machines:** pin dependencies and seed anything random, so CPU-dev and
  GPU-test results stay comparable. Expect CPU runs to be *slow* — develop against a tiny model or
  cached/mock responses, and treat the GPU as where real latency/quality is measured.

---

**How your existing skills slot in:** agent loop + memory → HW4; RAG/knowledge → HW3; tool/skill
contracts + deterministic verification → final project + the meta skill; CLI/GUI structure → HW2 +
the Streamlit skill. The genuinely *new* learning is **§1 Ollama specifics**, **§2 the tool-calling
agent loop**, and **§5 the smart-manufacturing domain + data**.
