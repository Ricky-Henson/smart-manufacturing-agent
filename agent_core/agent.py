"""agent.py — the probabilistic core (Qwen2.5 via Ollama).

The LLM only *explains*; it never decides. Two entry points:
  - `draft_rationale` — cited rationale for an already-decided disposition (ADR-4).
  - `ask` — the bounded `/ask` tool-calling loop: the model picks a skill, we run
    it, **verify** the result, feed it back, and loop; malformed/failed tool calls
    trigger **validate-then-retry** (PREP §1/§3). Read-only tools only — the loop
    cannot take an action, so it stays safe on a small local model.

Both take an injectable client (`llm=` / `model=`) so the logic is unit-tested
offline without a running Ollama.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from .config import settings
from .detector import Disposition
from .rag import SopClause
from .skills.get_lot_stats import run as gls_run, verify as gls_verify
from .skills.retrieve_sop import run as rs_run, verify as rs_verify

LLM = Callable[[str], str]


# ===========================================================================
# Disposition rationale (critical path) — decision is fixed, LLM explains only.
# ===========================================================================
def _build_prompt(disposition: Disposition, clauses: list[SopClause]) -> str:
    cited = "\n".join(f"[{c.cite_id}] ({c.source}) {c.text}" for c in clauses)
    breached = ", ".join(disposition.breached_params) or "none"
    return (
        "You are a wafer probe lot-disposition assistant. The disposition decision "
        "has ALREADY been made by deterministic QC rules — do NOT change it.\n"
        f"Lot: {disposition.lot_id}\n"
        f"Decision (fixed): {disposition.recommendation}\n"
        f"Breached parameters: {breached}\n\n"
        "Governing SOP clauses:\n"
        f"{cited}\n\n"
        f"Write a concise (2-4 sentence) rationale justifying the "
        f"{disposition.recommendation} decision, grounded ONLY in the clauses "
        "above. Cite clauses as [n]. Do not invent rules, limits, or numbers."
    )


def _ollama_chat(prompt: str) -> str:
    import ollama

    client = ollama.Client(host=settings.ollama_host)
    resp = client.chat(model=settings.model_name,
                       messages=[{"role": "user", "content": prompt}])
    return resp["message"]["content"]


def draft_rationale(disposition: Disposition, clauses: list[SopClause],
                    llm: LLM | None = None) -> str:
    """Draft a cited rationale for an already-decided disposition. LLM = explainer."""
    llm = _ollama_chat if llm is None else llm
    return llm(_build_prompt(disposition, clauses)).strip()


# ===========================================================================
# /ask — bounded tool-calling loop over one lot.
# ===========================================================================
# Read-only tools the model may call. lot_id is fixed by the caller, not the model.
TOOLS_SPEC = [
    {"type": "function", "function": {
        "name": "get_lot_stats",
        "description": "Parametric summary statistics for the current lot.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "retrieve_sop",
        "description": "Retrieve governing SOP clauses for a query string.",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"},
                                      "k": {"type": "integer"}},
                       "required": ["query"]}}},
]

# A chat client takes (messages, tools) and returns an assistant message dict
# shaped like Ollama's: {"content": str, "tool_calls": [{"function": {...}}]}.
Model = Callable[[list[dict], list[dict]], dict]


@dataclass
class AskResult:
    answer: str
    trace: list = field(default_factory=list)  # [{"tool","args","ok","error"?}]


def _ask_system(lot_id: str) -> str:
    return (
        f"You are answering questions about wafer probe lot {lot_id}. Use the tools "
        "to get facts — never invent numbers. get_lot_stats returns this lot's "
        "parametric stats; retrieve_sop returns governing SOP clauses for a query. "
        "Cite SOP sources when relevant. When you have enough information, answer "
        "concisely."
    )


def _dispatch(name, args, lot_id, data_dir, persist_dir, embedder) -> dict:
    """Run a tool and VERIFY its output before the loop trusts it."""
    if name == "get_lot_stats":
        out = gls_run.run(lot_id, data_dir=data_dir)
        gls_verify.verify({"lot_id": lot_id}, out)
        return out
    if name == "retrieve_sop":
        if "query" not in args:
            raise ValueError("retrieve_sop requires a 'query' argument")
        k = int(args.get("k", 4))
        out = rs_run.run(args["query"], k=k, persist_dir=persist_dir, embedder=embedder)
        rs_verify.verify({"query": args["query"], "k": k}, out)
        return out
    raise ValueError(f"unknown tool: {name!r}")


def _ollama_tool_chat(messages: list[dict], tools: list[dict]) -> dict:
    import ollama

    client = ollama.Client(host=settings.ollama_host)
    m = client.chat(model=settings.model_name, messages=messages, tools=tools)["message"]
    calls = []
    for tc in (getattr(m, "tool_calls", None) or []):
        calls.append({"function": {"name": tc.function.name,
                                   "arguments": dict(tc.function.arguments)}})
    return {"content": getattr(m, "content", "") or "", "tool_calls": calls}


def ask(lot_id: str, question: str, *, model: Model | None = None, data_dir=None,
        persist_dir=None, embedder=None, max_steps: int = 6, max_retries: int = 2) -> AskResult:
    """Bounded tool-calling Q&A loop over one lot. Tools are verified; bad calls retry."""
    model = _ollama_tool_chat if model is None else model
    messages = [{"role": "system", "content": _ask_system(lot_id)},
                {"role": "user", "content": question}]
    trace: list = []
    retries_left = max_retries

    for _ in range(max_steps):
        msg = model(messages, TOOLS_SPEC)
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return AskResult((msg.get("content") or "").strip(), trace)

        call = tool_calls[0]["function"]
        name, args = call.get("name"), (call.get("arguments") or {})
        messages.append({"role": "assistant", "content": msg.get("content") or "",
                         "tool_calls": tool_calls})
        try:
            result = _dispatch(name, args, lot_id, data_dir, persist_dir, embedder)
            trace.append({"tool": name, "args": args, "ok": True})
            messages.append({"role": "tool", "name": name, "content": json.dumps(result)})
        except Exception as exc:  # malformed/unknown/failed-verify -> validate-then-retry
            trace.append({"tool": name, "args": args, "ok": False, "error": str(exc)})
            if retries_left <= 0:
                return AskResult(f"Unable to answer: tool {name!r} failed ({exc}).", trace)
            retries_left -= 1
            messages.append({"role": "tool", "name": name or "unknown",
                             "content": f"ERROR: {exc}. Choose a valid tool and arguments."})

    return AskResult("Unable to answer within the step budget.", trace)
