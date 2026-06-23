"""shell.py — the DETERMINISTIC guard around the LLM.

Never trusts raw model output for an action. Validates (decision, lot, approver),
commits HOLD/RELEASE to the append-only audit log, and writes the disposition
report. Enforces SOP §5: every disposition needs a named approver; an override
needs a reason. No LLM here.

State + reports live under settings.memory_dir (the audit log is the source of
truth; current state = the latest log entry for a lot). Reports go to
memory_dir/reports/<lot>.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from . import memory
from .config import settings
from .detector import Disposition

Decision = Literal["HOLD", "RELEASE"]


class DispositionError(ValueError):
    """Raised when a disposition fails validation (bad decision / no approver / ...)."""


def _validate(lot_id: str, decision: str, approved_by: str) -> None:
    if decision not in ("HOLD", "RELEASE"):
        raise DispositionError(f"invalid decision: {decision!r}")
    if not lot_id:
        raise DispositionError("missing lot_id")
    if not approved_by or not approved_by.strip():
        raise DispositionError("a named approver is required (SOP 5.1)")


def _reports_dir(memory_dir=None) -> Path:
    d = Path(settings.memory_dir if memory_dir is None else memory_dir) / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_report(record: dict, memory_dir=None) -> Path:
    cites = ", ".join(record["clause_refs"]) or "—"
    override = ""
    if record["overridden"]:
        override = f" (override: {record['override_reason']})"
    body = (
        f"# Disposition report — {record['lot_id']}\n\n"
        f"- Decision: **{record['decision']}**{override}\n"
        f"- Approved by: {record['approved_by']}\n"
        f"- SOP clauses: {cites}\n"
        f"- Timestamp: {record['timestamp']}\n\n"
        f"## Rationale\n{record['rationale'] or '(none)'}\n"
    )
    path = _reports_dir(memory_dir) / f"{record['lot_id']}.md"
    path.write_text(body, encoding="utf-8")
    return path


def commit(lot_id: str, decision: Decision, *, approved_by: str, rationale: str,
           clause_refs=None, overridden: bool = False, override_reason=None,
           memory_dir=None) -> dict:
    """Validate, append to the audit log, and write the report. Returns the record."""
    _validate(lot_id, decision, approved_by)
    if overridden and not (override_reason and override_reason.strip()):
        raise DispositionError("an override requires a reason (SOP 5.2)")

    record = {
        "lot_id": lot_id,
        "decision": decision,
        "approved_by": approved_by,
        "overridden": overridden,
        "override_reason": override_reason,
        "rationale": rationale,
        "clause_refs": list(clause_refs or []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    memory.append(record, memory_dir)
    record["report"] = str(_write_report(record, memory_dir))
    return record


def approve(lot_id: str, disposition: Disposition, *, approved_by: str,
            rationale: str, memory_dir=None) -> dict:
    """Commit the drafted (deterministic) disposition as a human approval."""
    return commit(lot_id, disposition.recommendation, approved_by=approved_by,
                  rationale=rationale, clause_refs=disposition.clause_refs,
                  memory_dir=memory_dir)


def override(lot_id: str, decision: Decision, *, approved_by: str, reason: str,
             rationale: str = "", clause_refs=None, memory_dir=None) -> dict:
    """Record a human override of the drafted recommendation (reason required)."""
    return commit(lot_id, decision, approved_by=approved_by, rationale=rationale,
                  clause_refs=clause_refs, overridden=True, override_reason=reason,
                  memory_dir=memory_dir)


def state(lot_id: str, memory_dir=None) -> str | None:
    """Current committed decision for a lot, or None if never dispositioned."""
    rec = memory.latest_for(lot_id, memory_dir)
    return rec["decision"] if rec else None
