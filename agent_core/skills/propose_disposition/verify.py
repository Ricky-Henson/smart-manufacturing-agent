"""propose_disposition — deterministic verifier. No LLM.

Contract (SKILL.md): recommendation in {HOLD, RELEASE}; cite_ids non-empty and a
subset of the input clause ids; non-empty breached_params implies HOLD. The
verifier checks structure, not the rationale prose.
"""
from __future__ import annotations


def verify(inputs: dict, output: dict) -> None:
    if output["recommendation"] not in ("HOLD", "RELEASE"):
        raise ValueError("recommendation must be HOLD or RELEASE")

    input_ids = {c["cite_id"] for c in inputs["clauses"]}
    cite_ids = output["cite_ids"]
    if not cite_ids:
        raise ValueError("cite_ids must be non-empty")
    if not set(cite_ids) <= input_ids:
        raise ValueError("cite_ids must be a subset of the input clause ids")

    if inputs["breached_params"] and output["recommendation"] != "HOLD":
        raise ValueError("breached params require a HOLD recommendation")
