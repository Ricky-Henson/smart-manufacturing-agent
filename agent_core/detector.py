"""detector.py — DETERMINISTIC anomaly detection. No LLM in this decision.

Config-driven QC limits + simple statistical rules decide whether a lot is
`flagged` and which parameters breached. This is the heart of the deterministic
shell: classic code decides; the LLM (later) only explains the decision.

Three explainable rules per parameter, all deterministic:
  1. out_of_limit — fraction of dies outside [LSL, USL] exceeds MAX_OUT_FRAC
                    (catches outlier tails, edge patterns, large shifts).
  2. mean_shift   — lot mean is > MEAN_SHIFT_SIGMA baseline sigmas off nominal
                    (catches a uniform parametric shift).
  3. drift        — range of per-wafer means is > DRIFT_RANGE_SIGMA sigmas
                    (catches within-lot tool/sensor drift across wafers).
A parameter is breached if ANY rule fires; the lot is flagged if any parameter
is breached.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from . import ingest


# --- QC limits: set by PE/customers; the config that DRIVES detection. -------
# Deliberately separate from the generator's physics so eval stays honest.
# LSL/USL sit ~4 baseline sigmas off nominal (standard spec-limit practice).
@dataclass(frozen=True)
class ParamLimits:
    lsl: float
    usl: float
    base_mean: float
    base_sigma: float


QC_LIMITS: dict[str, ParamLimits] = {
    "Vt":      ParamLimits(lsl=0.37, usl=0.53, base_mean=0.45, base_sigma=0.02),
    "Idd":     ParamLimits(lsl=1.00, usl=1.40, base_mean=1.20, base_sigma=0.05),
    "leakage": ParamLimits(lsl=0.00, usl=2.46, base_mean=1.05, base_sigma=0.32),
}

# Rule thresholds (tunable; live here as the detector's config). These favor
# recall (catch bad lots) over precision: with realistic lot-to-lot process
# variation they yield F1~0.88 — not a trivial 1.0 — and a few healthy lots are
# over-flagged. Raising MEAN_SHIFT_SIGMA removes false alarms but misses subtle
# shifts (the classic tradeoff; see the sweep behind scripts/eval.py).
MAX_OUT_FRAC = 0.01        # >1% of dies out of spec -> breach
MEAN_SHIFT_SIGMA = 0.75    # |lot mean - nominal| beyond this many sigmas -> breach
DRIFT_RANGE_SIGMA = 1.5    # wafer-mean range beyond this many sigmas -> breach


@dataclass
class DetectionResult:
    lot_id: str
    flagged: bool
    breached_params: list[str]
    detail: dict  # per-param stats + which rules fired

    def to_dict(self) -> dict:
        return asdict(self)


def _evaluate_param(df: pd.DataFrame, param: str, lim: ParamLimits) -> dict:
    x = df[param].to_numpy()
    out_frac = float(((x < lim.lsl) | (x > lim.usl)).mean())
    lot_mean = float(x.mean())
    mean_shift_sigma = abs(lot_mean - lim.base_mean) / lim.base_sigma
    wafer_means = df.groupby("wafer_id")[param].mean()
    drift_range_sigma = float((wafer_means.max() - wafer_means.min()) / lim.base_sigma)

    rules = []
    if out_frac > MAX_OUT_FRAC:
        rules.append("out_of_limit")
    if mean_shift_sigma > MEAN_SHIFT_SIGMA:
        rules.append("mean_shift")
    if drift_range_sigma > DRIFT_RANGE_SIGMA:
        rules.append("drift")

    return {
        "param": param,
        "breached": bool(rules),
        "rules": rules,
        "out_frac": round(out_frac, 4),
        "lot_mean": round(lot_mean, 4),
        "std": round(float(x.std()), 4),
        "mean_shift_sigma": round(mean_shift_sigma, 2),
        "drift_range_sigma": round(drift_range_sigma, 2),
    }


def detect_lot(df: pd.DataFrame) -> DetectionResult:
    """Run the deterministic rules over one lot's DataFrame. Pure + testable."""
    lot_id = str(df["lot_id"].iloc[0])
    detail = {p: _evaluate_param(df, p, lim) for p, lim in QC_LIMITS.items()}
    breached = [p for p, d in detail.items() if d["breached"]]
    return DetectionResult(lot_id, bool(breached), breached, detail)


def detect(lot_id: str, data_dir=None) -> DetectionResult:
    """Load a lot and detect. The LLM is never consulted here."""
    return detect_lot(ingest.load_lot(lot_id, data_dir))


# --- Deterministic disposition policy (ADR-4): breach -> SOP clause + action --
# The HOLD/RELEASE decision is made HERE, by code, not by the LLM. The agent
# only writes the rationale for the decision computed below.
PARAM_CLAUSE = {"Vt": "QC-SOP.md#3.1", "leakage": "QC-SOP.md#3.4"}


@dataclass
class Disposition:
    lot_id: str
    recommendation: str          # "HOLD" or "RELEASE"
    breached_params: list[str]
    clause_refs: list[str]       # governing SOP clauses to cite
    escalate: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _clauses_for(detail: dict) -> list[str]:
    refs = []
    for param, d in detail.items():
        if not d["breached"]:
            continue
        if param == "Idd":
            refs.append("QC-SOP.md#3.3" if "drift" in d["rules"] else "QC-SOP.md#3.2")
        else:
            refs.append(PARAM_CLAUSE[param])
    return refs


def decide(result: DetectionResult) -> Disposition:
    """Map detection -> HOLD/RELEASE via the SOP rules. Deterministic; no LLM."""
    if not result.flagged:
        return Disposition(result.lot_id, "RELEASE", [], ["QC-SOP.md#4.1"], False)
    refs = _clauses_for(result.detail)
    escalate = len(result.breached_params) >= 2          # SOP 3.5 multiple breaches
    if escalate:
        refs.append("QC-SOP.md#3.5")
    return Disposition(result.lot_id, "HOLD", list(result.breached_params), refs, escalate)
