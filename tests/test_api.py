"""Tests for the FastAPI surface — TestClient with the AppContext overridden to
fakes (tmp data + fake index + fake LLMs). No Ollama.
"""
import pytest
from fastapi.testclient import TestClient

from agent_core import ingest, rag
from agent_core.api import AppContext, app, get_ctx
from scripts.generate_data import generate

VOCAB = ["vt", "idd", "leakage", "drift", "edge", "hold", "release",
         "approver", "escalate", "limit", "shift", "mean", "wafer", "tail"]


def _fake_embed(texts):
    return [[float(t.lower().count(w)) for w in VOCAB] + [1.0] for t in texts]


@pytest.fixture
def client(tmp_path):
    generate(tmp_path, seed=42)
    db = tmp_path / "db"
    rag.build_index(persist_dir=db, embedder=_fake_embed)

    def _ctx():
        return AppContext(
            data_dir=tmp_path, persist_dir=db, embedder=_fake_embed,
            memory_dir=tmp_path / "mem",
            draft_llm=lambda prompt: "Rationale grounded in the cited clause [1].",
            ask_model=lambda messages, tools: {"content": "It breaches the SOP limit."},
        )

    app.dependency_overrides[get_ctx] = _ctx
    yield TestClient(app)
    app.dependency_overrides.clear()


def _flagged_lot(tmp_path):
    from agent_core import detector
    return next(l for l in ingest.list_lots(tmp_path) if detector.detect(l, tmp_path).flagged)


def test_lots_lists_with_flags(client):
    body = client.get("/lots").json()
    assert len(body["lots"]) == 40
    assert any(lot["flagged"] for lot in body["lots"])


def test_lot_stats(client):
    body = client.get("/lot/LOT0000").json()
    assert body["n_die"] > 0 and set(body["params"]) == {"Vt", "Idd", "leakage"}


def test_lot_not_found(client):
    assert client.get("/lot/LOT9999").status_code == 404


def test_disposition_then_approve(client, tmp_path):
    lot = _flagged_lot(tmp_path)
    disp = client.get(f"/disposition/{lot}").json()
    assert disp["recommendation"] == "HOLD" and disp["clauses"]
    assert disp["rationale"].endswith("[1].")

    rec = client.post("/approve", json={"lot_id": lot, "approved_by": "alice",
                                        "rationale": disp["rationale"]}).json()
    assert rec["decision"] == "HOLD" and rec["approved_by"] == "alice"


def test_approve_requires_named_approver(client, tmp_path):
    lot = _flagged_lot(tmp_path)
    r = client.post("/approve", json={"lot_id": lot, "approved_by": "  ", "rationale": "x"})
    assert r.status_code == 400


def test_override(client, tmp_path):
    lot = ingest.list_lots(tmp_path)[0]
    rec = client.post("/override", json={"lot_id": lot, "decision": "RELEASE",
                                         "approved_by": "bob", "reason": "retest passed"}).json()
    assert rec["overridden"] and rec["decision"] == "RELEASE"


def test_ask(client):
    body = client.post("/ask", json={"lot_id": "LOT0000", "question": "why flagged?"}).json()
    assert body["answer"] == "It breaches the SOP limit."
    assert "trace" in body
