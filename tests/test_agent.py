"""Tests for the deterministic disposition (decide) and the LLM rationale draft.

`decide` is pure policy — unit-tested with constructed DetectionResults (robust to
data tuning) plus one real flagged lot. `draft_rationale` uses an injected fake LLM.
"""
from agent_core import detector, ingest
from agent_core.agent import draft_rationale
from agent_core.detector import DetectionResult, Disposition
from agent_core.rag import SopClause
from scripts.generate_data import generate


def _detail(**fired):
    """Build a detail dict; fired maps param -> list of rules ([] = not breached)."""
    return {p: {"breached": bool(fired.get(p, [])), "rules": fired.get(p, [])}
            for p in ("Vt", "Idd", "leakage")}


def test_decide_release_when_no_breach():
    disp = detector.decide(DetectionResult("L", False, [], _detail()))
    assert disp.recommendation == "RELEASE" and disp.clause_refs == ["QC-SOP.md#4.1"]


def test_decide_hold_idd_drift_cites_33():
    disp = detector.decide(DetectionResult("L", True, ["Idd"], _detail(Idd=["drift"])))
    assert disp.recommendation == "HOLD" and disp.clause_refs == ["QC-SOP.md#3.3"]


def test_decide_hold_idd_shift_cites_32():
    disp = detector.decide(DetectionResult("L", True, ["Idd"], _detail(Idd=["mean_shift"])))
    assert "QC-SOP.md#3.2" in disp.clause_refs


def test_decide_leakage_cites_34():
    disp = detector.decide(DetectionResult("L", True, ["leakage"], _detail(leakage=["out_of_limit"])))
    assert "QC-SOP.md#3.4" in disp.clause_refs


def test_decide_escalates_on_multiple_breaches():
    disp = detector.decide(DetectionResult(
        "LOTX", True, ["Vt", "Idd"], _detail(Vt=["out_of_limit"], Idd=["mean_shift"])))
    assert disp.escalate and "QC-SOP.md#3.5" in disp.clause_refs


def test_decide_on_a_real_flagged_lot(tmp_path):
    generate(tmp_path, seed=42)
    flagged = next(lot for lot in ingest.list_lots(tmp_path)
                   if detector.detect(lot, tmp_path).flagged)
    disp = detector.decide(detector.detect(flagged, tmp_path))
    assert disp.recommendation == "HOLD" and disp.clause_refs


def test_draft_rationale_grounds_in_decision_and_clauses():
    captured = {}

    def fake_llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return "Lot held: per-wafer Idd drift exceeds the limit [1]."

    disp = Disposition("LOT0001", "HOLD", ["Idd"], ["QC-SOP.md#3.3"], False)
    clauses = [SopClause(1, "QC-SOP.md#3.3", "Idd drifts across the lot -> HOLD.")]
    out = draft_rationale(disp, clauses, llm=fake_llm)

    assert out == "Lot held: per-wafer Idd drift exceeds the limit [1]."
    p = captured["prompt"]
    assert "HOLD" in p and "QC-SOP.md#3.3" in p and "[1]" in p
