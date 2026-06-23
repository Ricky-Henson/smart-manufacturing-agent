"""Tests for SOP retrieval — hermetic: a deterministic fake embedder, no Ollama.

Indexes the real `data_spec/QC-SOP.md` and checks that a breach query retrieves
the governing clause. The fake embedder is a keyword-count vector, which under
cosine distance ranks the clause sharing the query's terms highest.
"""
from agent_core import rag

VOCAB = ["vt", "idd", "leakage", "drift", "edge", "hold", "release",
         "approver", "escalate", "limit", "shift", "mean", "wafer", "tail"]


def _fake_embed(texts):
    vecs = []
    for t in texts:
        tl = t.lower()
        v = [float(tl.count(w)) for w in VOCAB]
        v.append(1.0)  # guard against an all-zero vector
        vecs.append(v)
    return vecs


def test_index_builds_all_clauses(tmp_path):
    n = rag.build_index(persist_dir=tmp_path / "db", embedder=_fake_embed)
    assert n >= 8  # scope, definitions, 3.1-3.5, release, approval, escalation


def test_idd_query_retrieves_idd_clause(tmp_path):
    db = tmp_path / "db"
    rag.build_index(persist_dir=db, embedder=_fake_embed)
    hits = rag.retrieve("Idd current over the limit, a uniform shift",
                        k=3, persist_dir=db, embedder=_fake_embed)
    assert any(("3.2" in h.source or "3.3" in h.source) for h in hits)
    assert [h.cite_id for h in hits] == list(range(1, len(hits) + 1))  # 1-based contiguous


def test_leakage_query_retrieves_edge_clause(tmp_path):
    db = tmp_path / "db"
    rag.build_index(persist_dir=db, embedder=_fake_embed)
    hits = rag.retrieve("leakage elevated on edge dies above the limit",
                        k=3, persist_dir=db, embedder=_fake_embed)
    assert any("3.4" in h.source for h in hits)
