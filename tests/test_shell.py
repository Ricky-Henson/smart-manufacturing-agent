"""Tests for the deterministic shell: validation guardrails + audit log + report."""
import pytest

from agent_core import memory, shell
from agent_core.detector import Disposition


def test_commit_writes_log_report_and_state(tmp_path):
    rec = shell.commit("LOT0001", "HOLD", approved_by="alice",
                       rationale="Idd drift [1].", clause_refs=["QC-SOP.md#3.3"],
                       memory_dir=tmp_path)
    # audit log is the source of truth
    assert memory.latest_for("LOT0001", tmp_path)["decision"] == "HOLD"
    assert shell.state("LOT0001", tmp_path) == "HOLD"
    # report written and references the clause
    report = (tmp_path / "reports" / "LOT0001.md").read_text(encoding="utf-8")
    assert "HOLD" in report and "QC-SOP.md#3.3" in report and "alice" in report
    assert rec["report"].endswith("LOT0001.md")


def test_named_approver_required(tmp_path):
    with pytest.raises(shell.DispositionError):
        shell.commit("LOT0001", "HOLD", approved_by="  ", rationale="x", memory_dir=tmp_path)


def test_invalid_decision_rejected(tmp_path):
    with pytest.raises(shell.DispositionError):
        shell.commit("LOT0001", "SCRAP", approved_by="alice", rationale="x", memory_dir=tmp_path)


def test_override_requires_reason(tmp_path):
    with pytest.raises(shell.DispositionError):
        shell.override("LOT0001", "RELEASE", approved_by="bob", reason="", memory_dir=tmp_path)
    rec = shell.override("LOT0001", "RELEASE", approved_by="bob",
                         reason="confirmed false alarm by PE", memory_dir=tmp_path)
    assert rec["overridden"] and rec["decision"] == "RELEASE"


def test_approve_uses_deterministic_recommendation(tmp_path):
    disp = Disposition("LOT0002", "HOLD", ["Idd"], ["QC-SOP.md#3.2"], False)
    rec = shell.approve("LOT0002", disp, approved_by="carol",
                        rationale="Idd shift [1].", memory_dir=tmp_path)
    assert rec["decision"] == "HOLD" and rec["clause_refs"] == ["QC-SOP.md#3.2"]


def test_log_is_append_only(tmp_path):
    shell.commit("LOT0003", "HOLD", approved_by="alice", rationale="a", memory_dir=tmp_path)
    shell.override("LOT0003", "RELEASE", approved_by="bob", reason="re-test passed",
                   memory_dir=tmp_path)
    history = [r for r in memory.read_all(tmp_path) if r["lot_id"] == "LOT0003"]
    assert len(history) == 2                      # both events retained
    assert shell.state("LOT0003", tmp_path) == "RELEASE"   # latest wins
