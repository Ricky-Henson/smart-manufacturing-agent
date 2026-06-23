"""Tests for the /ask tool-calling loop — scripted fake model, no Ollama.

Exercises: multi-step tool use + verification, validate-then-retry on a bad tool
call, and giving up after the retry budget.
"""
from agent_core import ingest, rag
from agent_core.agent import AskResult, ask
from scripts.generate_data import generate

VOCAB = ["vt", "idd", "leakage", "drift", "edge", "hold", "release",
         "approver", "escalate", "limit", "shift", "mean", "wafer", "tail"]


def _fake_embed(texts):
    return [[float(t.lower().count(w)) for w in VOCAB] + [1.0] for t in texts]


def _scripted(*messages):
    it = iter(messages)
    return lambda msgs, tools: next(it)


def _tool_call(name, **args):
    return {"content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]}


def _final(text):
    return {"content": text}


def test_ask_runs_tools_then_answers(tmp_path):
    generate(tmp_path, seed=42)
    db = tmp_path / "db"
    rag.build_index(persist_dir=db, embedder=_fake_embed)
    lot = ingest.list_lots(tmp_path)[0]

    model = _scripted(
        _tool_call("get_lot_stats"),
        _tool_call("retrieve_sop", query="Idd over the limit", k=2),
        _final("The lot's parametrics and SOP [1] explain the flag."),
    )
    res = ask(lot, "Why might this lot be flagged?", model=model,
              data_dir=tmp_path, persist_dir=db, embedder=_fake_embed)

    assert isinstance(res, AskResult)
    assert res.answer.startswith("The lot")
    assert [s["tool"] for s in res.trace] == ["get_lot_stats", "retrieve_sop"]
    assert all(s["ok"] for s in res.trace)


def test_ask_retries_on_bad_tool_call(tmp_path):
    generate(tmp_path, seed=42)
    lot = ingest.list_lots(tmp_path)[0]

    model = _scripted(
        _tool_call("frobnicate"),                 # unknown tool -> error -> retry
        _final("Recovered and answered."),
    )
    res = ask(lot, "q", model=model, data_dir=tmp_path)

    assert res.answer == "Recovered and answered."
    assert res.trace[0]["ok"] is False
    assert "unknown tool" in res.trace[0]["error"]


def test_ask_gives_up_after_retry_budget(tmp_path):
    generate(tmp_path, seed=42)
    lot = ingest.list_lots(tmp_path)[0]

    model = _scripted(*[_tool_call("bad")] * 5)
    res = ask(lot, "q", model=model, data_dir=tmp_path, max_steps=6, max_retries=2)

    assert "Unable to answer" in res.answer
    assert all(s["ok"] is False for s in res.trace)
