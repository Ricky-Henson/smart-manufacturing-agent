"""Tests for the Hermes-style skills: run() produces, verify() proves (and catches).

Hermetic — fake embedder for RAG, fake LLM for the rationale; no Ollama.
"""
import pytest

from agent_core import detector, ingest, rag
from agent_core.skills.get_lot_stats import run as gls_run, verify as gls_verify
from agent_core.skills.propose_disposition import run as pd_run, verify as pd_verify
from agent_core.skills.retrieve_sop import run as rs_run, verify as rs_verify
from scripts.generate_data import generate

VOCAB = ["vt", "idd", "leakage", "drift", "edge", "hold", "release",
         "approver", "escalate", "limit", "shift", "mean", "wafer", "tail"]


def _fake_embed(texts):
    return [[float(t.lower().count(w)) for w in VOCAB] + [1.0] for t in texts]


def _fake_llm(prompt):
    return "Rationale grounded in the cited clause [1]."


# --- get_lot_stats ---------------------------------------------------------
def test_get_lot_stats_runs_and_verifies(tmp_path):
    generate(tmp_path, seed=42)
    lot = ingest.list_lots(tmp_path)[0]
    out = gls_run.run(lot, data_dir=tmp_path)
    gls_verify.verify({"lot_id": lot}, out)        # must not raise
    assert out["n_die"] > 0
    assert set(out["params"]) == {"Vt", "Idd", "leakage"}


def test_get_lot_stats_verify_catches_impossible_breach(tmp_path):
    generate(tmp_path, seed=42)
    lot = ingest.list_lots(tmp_path)[0]
    out = gls_run.run(lot, data_dir=tmp_path)
    out["params"]["Vt"]["n_breach"] = out["n_die"] + 1   # more breaches than dies
    with pytest.raises(ValueError):
        gls_verify.verify({"lot_id": lot}, out)


# --- retrieve_sop ----------------------------------------------------------
def test_retrieve_sop_runs_and_verifies(tmp_path):
    db = tmp_path / "db"
    rag.build_index(persist_dir=db, embedder=_fake_embed)
    inp = {"query": "Idd uniform shift over the limit", "k": 3}
    out = rs_run.run(inp["query"], k=inp["k"], persist_dir=db, embedder=_fake_embed)
    rs_verify.verify(inp, out)
    assert 1 <= len(out["clauses"]) <= 3


# --- propose_disposition ---------------------------------------------------
def test_propose_disposition_runs_and_verifies():
    clauses = [{"cite_id": 1, "source": "QC-SOP.md#3.2", "text": "Idd shift -> HOLD."}]
    inp = {"lot_id": "LOT0001", "breached_params": ["Idd"], "clauses": clauses}
    out = pd_run.run("LOT0001", ["Idd"], clauses, llm=_fake_llm)
    pd_verify.verify(inp, out)
    assert out["recommendation"] == "HOLD" and out["cite_ids"] == [1]


def test_propose_disposition_verify_catches_breach_without_hold():
    clauses = [{"cite_id": 1, "source": "QC-SOP.md#3.2", "text": "..."}]
    bad = {"lot_id": "L", "recommendation": "RELEASE", "breached_params": ["Idd"],
           "cite_ids": [1], "rationale": "x"}
    with pytest.raises(ValueError):
        pd_verify.verify({"lot_id": "L", "breached_params": ["Idd"], "clauses": clauses}, bad)


# --- end-to-end: the three skills chained, each verified -------------------
def test_pipeline_stats_retrieve_propose(tmp_path):
    generate(tmp_path, seed=42)
    db = tmp_path / "db"
    rag.build_index(persist_dir=db, embedder=_fake_embed)
    lot = next(l for l in ingest.list_lots(tmp_path) if detector.detect(l, tmp_path).flagged)

    breached = detector.detect(lot, tmp_path).breached_params
    assert breached

    stats = gls_run.run(lot, data_dir=tmp_path)
    gls_verify.verify({"lot_id": lot}, stats)

    query = " ".join(breached) + " over the limit"
    sop = rs_run.run(query, k=3, persist_dir=db, embedder=_fake_embed)
    rs_verify.verify({"query": query, "k": 3}, sop)

    inp = {"lot_id": lot, "breached_params": breached, "clauses": sop["clauses"]}
    proposal = pd_run.run(lot, breached, sop["clauses"], llm=_fake_llm)
    pd_verify.verify(inp, proposal)
    assert proposal["recommendation"] == "HOLD"
