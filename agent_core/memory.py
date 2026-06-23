"""memory.py — disposition audit log + recall (HW4 patterns).

Append-only JSONL log under settings.memory_dir is the **source of truth** for
every committed disposition (decision + approver + override). Optional BM25/hybrid
recall comes later (PLAN "Memory: Both" — log + markdown index).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import settings

LOG_NAME = "dispositions.jsonl"


def _log_path(memory_dir=None) -> Path:
    d = Path(settings.memory_dir if memory_dir is None else memory_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d / LOG_NAME


def append(record: dict, memory_dir=None) -> None:
    """Append one disposition event to the append-only audit log."""
    with _log_path(memory_dir).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def read_all(memory_dir=None) -> list[dict]:
    """Every logged event, in order."""
    path = _log_path(memory_dir)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def latest_for(lot_id: str, memory_dir=None) -> dict | None:
    """The most recent committed disposition for a lot (current state)."""
    matches = [r for r in read_all(memory_dir) if r.get("lot_id") == lot_id]
    return matches[-1] if matches else None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _document(record: dict) -> str:
    """Searchable text for one disposition record."""
    parts = [
        record.get("lot_id", ""),
        record.get("decision", ""),
        record.get("approved_by", ""),
        " ".join(record.get("clause_refs") or []),
        record.get("rationale") or "",
        record.get("override_reason") or "",
    ]
    if record.get("overridden"):
        parts.append("override")
    return " ".join(parts)


def recall(query: str, k: int = 5, memory_dir=None) -> list[dict]:
    """BM25 recall over past dispositions. Returns top-k records (with `_score`)."""
    from rank_bm25 import BM25Okapi

    records = read_all(memory_dir)
    if not records or not query.strip():
        return []
    bm25 = BM25Okapi([_tokenize(_document(r)) for r in records])
    scores = bm25.get_scores(_tokenize(query))

    ranked = sorted(range(len(records)), key=lambda i: (-scores[i], i))
    out = []
    for i in ranked[:k]:
        if scores[i] <= 0:
            break
        rec = dict(records[i])
        rec["_score"] = round(float(scores[i]), 4)
        out.append(rec)
    return out


def render_markdown_index(memory_dir=None) -> Path:
    """Render the audit log to a markdown table (PLAN: markdown index for demo/teaching)."""
    records = read_all(memory_dir)
    lines = ["# Disposition index", "",
             "| lot | decision | approver | clauses | override |",
             "|---|---|---|---|---|"]
    for r in records:
        clauses = ", ".join(r.get("clause_refs") or []) or "—"
        override = r.get("override_reason") if r.get("overridden") else None
        lines.append(f"| {r['lot_id']} | {r['decision']} | {r.get('approved_by', '')} "
                     f"| {clauses} | {override or '—'} |")
    path = Path(settings.memory_dir if memory_dir is None else memory_dir) / "index.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
