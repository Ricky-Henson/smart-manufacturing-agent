"""retrieve_sop — deterministic verifier. No LLM.

Contract (SKILL.md): len(clauses) <= k; cite_id is 1-based contiguous by rank;
each clause has non-empty source and text.
"""
from __future__ import annotations


def verify(inputs: dict, output: dict) -> None:
    clauses = output["clauses"]
    k = inputs.get("k", 4)
    if len(clauses) > k:
        raise ValueError(f"returned {len(clauses)} clauses > k={k}")
    ids = [c["cite_id"] for c in clauses]
    if ids != list(range(1, len(ids) + 1)):
        raise ValueError("cite_id must be 1-based contiguous by rank")
    for c in clauses:
        if not c.get("source") or not c.get("text"):
            raise ValueError("clause missing source/text")
