"""Tests for the synthetic data generator: reproducibility + schema/label invariants."""
import filecmp

import pandas as pd

from scripts.generate_data import COLUMNS, FAILURE_MODES, N_LOTS, WAFER_RADIUS, generate


def test_same_seed_is_byte_identical(tmp_path):
    a = generate(tmp_path / "a", seed=123)
    b = generate(tmp_path / "b", seed=123)
    files = sorted(p.name for p in a.iterdir())
    assert files == sorted(p.name for p in b.iterdir())
    _, mismatch, errors = filecmp.cmpfiles(a, b, files, shallow=False)
    assert not mismatch and not errors, (mismatch, errors)


def test_labels_and_schema(tmp_path):
    out = generate(tmp_path, seed=7)
    labels = pd.read_csv(out / "labels.csv")

    assert len(labels) == N_LOTS
    assert set(labels["failure_mode"]).issubset(set(FAILURE_MODES))
    assert (labels["is_anomalous"] == (labels["failure_mode"] != "none")).all()
    # a usable eval set needs both classes present
    assert labels["is_anomalous"].any() and (~labels["is_anomalous"]).any()

    lot = pd.read_csv(out / f"{labels.iloc[0]['lot_id']}.csv")
    assert list(lot.columns) == COLUMNS
    assert (lot["leakage"] > 0).all()                       # leakage is positive
    r = (lot["die_x"] ** 2 + lot["die_y"] ** 2) ** 0.5
    assert (r <= WAFER_RADIUS).all()                        # dies inside the wafer
