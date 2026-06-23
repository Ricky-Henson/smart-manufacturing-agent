"""get_lot_stats — deterministic implementation. Wires `ingest` + detector QC limits."""
from __future__ import annotations

from agent_core import detector, ingest


def run(lot_id: str, data_dir=None) -> dict:
    df = ingest.load_lot(lot_id, data_dir)
    n_die = int(len(df))
    params = {}
    for param, lim in detector.QC_LIMITS.items():
        x = df[param]
        n_breach = int(((x < lim.lsl) | (x > lim.usl)).sum())
        params[param] = {
            "mean": round(float(x.mean()), 4),
            "std": round(float(x.std()), 4),
            "min": round(float(x.min()), 4),
            "max": round(float(x.max()), 4),
            "limit": lim.usl,
            "n_breach": n_breach,
        }
    return {"lot_id": lot_id, "n_die": n_die, "params": params}
