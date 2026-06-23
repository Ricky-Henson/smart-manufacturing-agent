"""get_lot_stats — deterministic verifier. No LLM.

Contract (SKILL.md): lot_id echoes input; n_die >= 0; each param block has
{mean, std, min, max, limit, n_breach}; 0 <= n_breach <= n_die.
"""
from __future__ import annotations

_REQUIRED = {"mean", "std", "min", "max", "limit", "n_breach"}


def verify(inputs: dict, output: dict) -> None:
    if output["lot_id"] != inputs["lot_id"]:
        raise ValueError("lot_id must echo the input")
    n_die = output["n_die"]
    if n_die < 0:
        raise ValueError("n_die must be >= 0")
    for param, block in output["params"].items():
        missing = _REQUIRED - set(block)
        if missing:
            raise ValueError(f"{param} missing keys: {sorted(missing)}")
        if not 0 <= block["n_breach"] <= n_die:
            raise ValueError(f"{param} n_breach out of range [0, {n_die}]")
