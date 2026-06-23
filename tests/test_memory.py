"""Tests for memory: BM25 recall over the disposition log + the markdown index."""
from agent_core import memory, shell


def _seed(memory_dir):
    shell.commit("LOT0001", "HOLD", approved_by="alice",
                 rationale="Idd uniform shift over the limit",
                 clause_refs=["QC-SOP.md#3.2"], memory_dir=memory_dir)
    shell.commit("LOT0002", "HOLD", approved_by="alice",
                 rationale="leakage elevated on edge dies",
                 clause_refs=["QC-SOP.md#3.4"], memory_dir=memory_dir)
    shell.commit("LOT0003", "RELEASE", approved_by="bob",
                 rationale="no breach detected", memory_dir=memory_dir)


def test_recall_ranks_relevant_first(tmp_path):
    _seed(tmp_path)
    hits = memory.recall("edge leakage pattern", k=2, memory_dir=tmp_path)
    assert hits and hits[0]["lot_id"] == "LOT0002"
    assert "_score" in hits[0]


def test_recall_empty_log_or_blank_query(tmp_path):
    assert memory.recall("anything", memory_dir=tmp_path) == []   # no log yet
    _seed(tmp_path)
    assert memory.recall("   ", memory_dir=tmp_path) == []         # blank query


def test_markdown_index_lists_all_lots(tmp_path):
    _seed(tmp_path)
    text = memory.render_markdown_index(tmp_path).read_text(encoding="utf-8")
    assert "LOT0001" in text and "LOT0002" in text and "LOT0003" in text
    assert "decision" in text and "QC-SOP.md#3.4" in text
