"""eval.py — detection Precision / Recall / F1 on the labeled synthetic lots.

Runs the deterministic detector over every labeled lot and scores `flagged`
against ground truth (success metric #1), with a per-failure-mode breakdown so you
can see which anomalies are subtle. Pure function `score()` is reused by tests;
`main()` prints a report.

Run:  python -m scripts.eval
"""
from __future__ import annotations

from agent_core import detector, ingest


def score(data_dir=None) -> dict:
    """Confusion counts + P/R/F1 of `flagged` vs `is_anomalous`, plus by-mode recall."""
    labels = ingest.load_labels(data_dir)
    pred = {lot_id: detector.detect(lot_id, data_dir).flagged
            for lot_id in ingest.list_lots(data_dir)}

    tp = fp = fn = tn = 0
    by_mode: dict[str, dict] = {}
    for row in labels.itertuples():
        y, yhat = bool(row.is_anomalous), pred[row.lot_id]
        tp += y and yhat
        fp += (not y) and yhat
        fn += y and (not yhat)
        tn += (not y) and (not yhat)
        d = by_mode.setdefault(row.failure_mode, {"flagged": 0, "total": 0})
        d["total"] += 1
        d["flagged"] += int(yhat)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn, "by_mode": by_mode}


def main() -> None:
    m = score()
    print(f"Detection on {m['tp'] + m['fn']} anomalous / {m['fp'] + m['tn']} healthy lots:")
    print(f"  precision={m['precision']:.3f}  recall={m['recall']:.3f}  f1={m['f1']:.3f}")
    print(f"  tp={m['tp']} fp={m['fp']} fn={m['fn']} tn={m['tn']}")
    print("  by failure mode (flagged / total):")
    for mode, d in sorted(m["by_mode"].items()):
        print(f"    {mode:14s} {d['flagged']}/{d['total']}")
    print("  (fp = healthy lots over-flagged by process drift; fn = subtle anomalies "
          "missed. Thresholds favor recall — see detector.py.)")


if __name__ == "__main__":
    main()
