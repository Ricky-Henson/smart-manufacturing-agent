"""generate_data.py — synthetic parametric probe data generator.

The first real module: everything downstream (detector, RAG, eval, demo) depends
on having labeled lots. Produces seeded synthetic wafer-probe data with injected,
labeled failure modes so the deterministic detector can be scored (P/R/F1).

Two principles:
  - **Deterministic:** same seed -> byte-identical files on CPU and the A6000.
  - **Honest eval:** the generator models the process *physics* (nominal
    distributions + injected anomalies) and deliberately does NOT know the
    detector's limits, so detection isn't graded against its own cheat sheet.

Run:  python -m scripts.generate_data        # writes to settings.data_dir
See:  data_spec/SCHEMA.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from agent_core.config import settings

# --- Generation constants (the synthetic "process") -------------------------
N_LOTS = 40
WAFERS_PER_LOT = 25
WAFER_RADIUS = 8                       # die-grid radius; circular wafer (~201 dies)

# Nominal parametric distributions (healthy process)
VT_MEAN, VT_STD = 0.45, 0.02           # threshold voltage (V)
IDD_MEAN, IDD_STD = 1.20, 0.05         # supply current (mA)
LEAK_LOG_MEAN, LEAK_LOG_STD = 0.0, 0.30  # leakage (nA): lognormal -> positive

# Lot-level process variation: a realistic per-lot baseline drift applied to ALL
# dies (healthy and anomalous alike). This is what makes detection non-trivial —
# a naive threshold mistakes normal lot-to-lot drift for an anomaly.
PROC_VT, PROC_IDD, PROC_LEAK_LOG = 0.008, 0.025, 0.10

# Injected anomaly magnitudes — deliberately SUBTLE (a few process sigmas), so the
# detector is good-but-not-perfect and its thresholds actually matter.
IDD_SHIFT = 0.09                       # idd_shift: uniform lot shift
DRIFT_MAX = 0.07                       # tool_drift: max within-lot drift across wafers
VT_TAIL_FRAC, VT_TAIL_LOW, VT_TAIL_HIGH = 0.015, 0.07, 0.16   # vt_tail outliers
EDGE_R, EDGE_MULT_LOW, EDGE_MULT_HIGH = 0.80, 1.9, 2.8        # edge_leakage

FAILURE_MODES = ["none", "idd_shift", "vt_tail", "edge_leakage", "tool_drift"]
MODE_WEIGHTS = [0.40, 0.15, 0.15, 0.15, 0.15]   # ~40% healthy; sums to 1.0

COLUMNS = ["lot_id", "wafer_id", "die_x", "die_y", "Vt", "Idd", "leakage"]


def _die_grid(radius: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Integer die coordinates inside a circular wafer + each die's r/R in [0,1]."""
    xs, ys = np.meshgrid(np.arange(-radius, radius + 1), np.arange(-radius, radius + 1))
    xs, ys = xs.ravel(), ys.ravel()
    r = np.sqrt(xs**2 + ys**2)
    keep = r <= radius
    return xs[keep], ys[keep], r[keep] / radius


def _generate_lot(lot_idx: int, mode: str, seed: int) -> pd.DataFrame:
    """One lot: WAFERS_PER_LOT wafers of die-level parametrics, with `mode` injected."""
    rng = np.random.default_rng(seed * 10_000 + lot_idx)
    die_x, die_y, r_norm = _die_grid(WAFER_RADIUS)
    n_die = die_x.size

    # Lot-level process variation, applied to every die in the lot.
    vt_offset = float(rng.normal(0.0, PROC_VT))
    idd_offset = float(rng.normal(0.0, PROC_IDD))
    leak_log_offset = float(rng.normal(0.0, PROC_LEAK_LOG))

    frames = []
    for wafer_id in range(1, WAFERS_PER_LOT + 1):
        vt = rng.normal(VT_MEAN, VT_STD, n_die) + vt_offset
        idd = rng.normal(IDD_MEAN, IDD_STD, n_die) + idd_offset
        leak = rng.lognormal(LEAK_LOG_MEAN + leak_log_offset, LEAK_LOG_STD, n_die)

        if mode == "idd_shift":
            idd += IDD_SHIFT
        elif mode == "tool_drift":
            idd += DRIFT_MAX * (wafer_id - 1) / (WAFERS_PER_LOT - 1)   # within-lot drift
        elif mode == "vt_tail":
            tail = rng.random(n_die) < VT_TAIL_FRAC
            vt[tail] += rng.uniform(VT_TAIL_LOW, VT_TAIL_HIGH, int(tail.sum()))
        elif mode == "edge_leakage":
            edge = r_norm > EDGE_R
            leak[edge] *= rng.uniform(EDGE_MULT_LOW, EDGE_MULT_HIGH, int(edge.sum()))

        frames.append(pd.DataFrame({
            "lot_id": f"LOT{lot_idx:04d}",
            "wafer_id": wafer_id,
            "die_x": die_x,
            "die_y": die_y,
            "Vt": vt.round(4),
            "Idd": idd.round(4),
            "leakage": leak.round(4),
        }))
    return pd.concat(frames, ignore_index=True)[COLUMNS]


def generate(out_dir: Path | str, seed: int | None = None) -> Path:
    """Write every lot CSV + labels.csv to out_dir. Seeded; returns out_dir."""
    seed = settings.seed if seed is None else seed
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    modes = np.random.default_rng(seed).choice(FAILURE_MODES, size=N_LOTS, p=MODE_WEIGHTS)

    labels = []
    for lot_idx, mode in enumerate(modes):
        lot_id = f"LOT{lot_idx:04d}"
        _generate_lot(lot_idx, str(mode), seed).to_csv(out_dir / f"{lot_id}.csv", index=False)
        labels.append({"lot_id": lot_id, "is_anomalous": mode != "none", "failure_mode": str(mode)})

    pd.DataFrame(labels).to_csv(out_dir / "labels.csv", index=False)
    return out_dir


def main() -> None:
    out = generate(settings.data_dir, settings.seed)
    print(f"wrote {N_LOTS} lots + labels.csv to {out}")


if __name__ == "__main__":
    main()
