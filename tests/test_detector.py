"""Tests for the deterministic detector: credible (non-perfect) metrics + per-mode."""
from agent_core import detector, ingest
from scripts.eval import score
from scripts.generate_data import generate


def _mode_breaches(labels, mode, data_dir):
    lots = labels[labels.failure_mode == mode]["lot_id"]
    return [detector.detect(lot, data_dir).breached_params for lot in lots]


def test_metrics_are_credible_not_perfect(tmp_path):
    generate(tmp_path, seed=42)
    m = score(tmp_path)
    assert 0.80 <= m["f1"] < 1.0          # good, but no longer trivially perfect
    assert m["recall"] >= 0.78
    assert m["precision"] >= 0.85
    assert m["fp"] + m["fn"] >= 1          # real errors -> a meaningful eval


def test_each_mode_flags_its_parameter(tmp_path):
    generate(tmp_path, seed=42)
    labels = ingest.load_labels(tmp_path)

    edge = _mode_breaches(labels, "edge_leakage", tmp_path)
    assert sum("leakage" in b for b in edge) >= 0.8 * len(edge)   # strongest signal

    idd = _mode_breaches(labels, "idd_shift", tmp_path)
    assert sum("Idd" in b for b in idd) >= 0.5 * len(idd)

    vt = _mode_breaches(labels, "vt_tail", tmp_path)
    assert any("Vt" in b for b in vt)

    none = _mode_breaches(labels, "none", tmp_path)
    assert sum(bool(b) for b in none) <= 0.3 * len(none)         # FPs are the exception


def test_tool_drift_can_fire_the_drift_rule(tmp_path):
    generate(tmp_path, seed=42)
    labels = ingest.load_labels(tmp_path)
    drift_lots = labels[labels.failure_mode == "tool_drift"]["lot_id"]
    assert any("drift" in detector.detect(lot, tmp_path).detail["Idd"]["rules"]
               for lot in drift_lots)
