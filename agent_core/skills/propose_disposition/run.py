"""propose_disposition — assemble a drafted proposal. Proposal only; never commits.

The recommendation is deterministic (breach -> HOLD, else RELEASE; ADR-4); the LLM
(injectable) only writes the cited rationale.
"""
from __future__ import annotations

from agent_core.agent import draft_rationale
from agent_core.detector import Disposition
from agent_core.rag import SopClause


def run(lot_id: str, breached_params, clauses, llm=None) -> dict:
    breached = list(breached_params)
    recommendation = "HOLD" if breached else "RELEASE"
    cite_ids = [c["cite_id"] for c in clauses]

    disposition = Disposition(lot_id, recommendation, breached,
                              [c["source"] for c in clauses], len(breached) >= 2)
    sop = [SopClause(c["cite_id"], c["source"], c["text"]) for c in clauses]
    rationale = draft_rationale(disposition, sop, llm=llm)

    return {
        "lot_id": lot_id,
        "recommendation": recommendation,
        "breached_params": breached,
        "cite_ids": cite_ids,
        "rationale": rationale,
    }
