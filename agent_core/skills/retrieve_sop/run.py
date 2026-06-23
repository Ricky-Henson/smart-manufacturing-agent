"""retrieve_sop — deterministic implementation (delegates to `rag.retrieve`)."""
from __future__ import annotations

from agent_core import rag


def run(query: str, k: int = 4, persist_dir=None, embedder=None) -> dict:
    clauses = rag.retrieve(query, k=k, persist_dir=persist_dir, embedder=embedder)
    return {"clauses": [{"cite_id": c.cite_id, "source": c.source, "text": c.text}
                        for c in clauses]}
