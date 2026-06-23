"""ingest.py — load a lot's parametric probe data.

Pure I/O + shaping; no detection logic and no LLM. Reads the CSVs produced by
`scripts/generate_data.py` from settings.data_dir (override `data_dir` for tests).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import settings


def _root(data_dir: Path | str | None) -> Path:
    return Path(settings.data_dir if data_dir is None else data_dir)


def list_lots(data_dir: Path | str | None = None) -> list[str]:
    """All lot ids available under the data root (sorted)."""
    return sorted(p.stem for p in _root(data_dir).glob("LOT*.csv"))


def load_lot(lot_id: str, data_dir: Path | str | None = None) -> pd.DataFrame:
    """Return one lot's die-level parametric records."""
    path = _root(data_dir) / f"{lot_id}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def load_labels(data_dir: Path | str | None = None) -> pd.DataFrame:
    """Ground-truth labels (lot_id, is_anomalous, failure_mode) for eval."""
    return pd.read_csv(_root(data_dir) / "labels.csv")
