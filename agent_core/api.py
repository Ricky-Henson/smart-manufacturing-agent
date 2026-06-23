"""api.py — FastAPI app (:8000). The HTTP surface the Spring Boot UI calls.

Thin wiring only — each handler delegates to the agent core. The LLM-touching
endpoints (`/disposition`, `/ask`) and the data/index/memory locations are pulled
from an injectable `AppContext` dependency: production uses real Ollama + the
`.env` roots; tests override `get_ctx` with fakes, so the suite stays hermetic.

Run:  uvicorn agent_core.api:app --host $AGENT_HOST --port $AGENT_PORT
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from . import agent, detector, ingest, rag, shell
from .config import settings
from .skills.get_lot_stats import run as gls_run

app = FastAPI(title="Probe Lot-Disposition Agent", version="0.1.0")


# --- Injectable context (real Ollama + .env roots by default) ---------------
@dataclass
class AppContext:
    data_dir: object = None
    persist_dir: object = None
    embedder: object = None
    memory_dir: object = None
    draft_llm: Callable | None = None
    ask_model: Callable | None = None


def get_ctx() -> AppContext:
    return AppContext(draft_llm=agent._ollama_chat, ask_model=agent._ollama_tool_chat)


# --- Request bodies ---------------------------------------------------------
class ApproveReq(BaseModel):
    lot_id: str
    approved_by: str
    rationale: str = ""


class OverrideReq(BaseModel):
    lot_id: str
    decision: str
    approved_by: str
    reason: str
    rationale: str = ""


class AskReq(BaseModel):
    lot_id: str
    question: str


def _disposition_payload(lot_id: str, ctx: AppContext) -> dict:
    result = detector.detect(lot_id, ctx.data_dir)        # raises FileNotFoundError
    disp = detector.decide(result)
    query = " ".join(disp.breached_params) or "lot released no breach"
    clauses = rag.retrieve(query, k=4, persist_dir=ctx.persist_dir, embedder=ctx.embedder)
    rationale = agent.draft_rationale(disp, clauses, llm=ctx.draft_llm)
    return {
        "lot_id": lot_id,
        "recommendation": disp.recommendation,
        "breached_params": disp.breached_params,
        "clause_refs": disp.clause_refs,
        "escalate": disp.escalate,
        "clauses": [{"cite_id": c.cite_id, "source": c.source, "text": c.text} for c in clauses],
        "rationale": rationale,
    }


# --- Endpoints --------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": settings.model_name}


@app.get("/lots")
def get_lots(ctx: AppContext = Depends(get_ctx)) -> dict:
    lots = []
    for lot_id in ingest.list_lots(ctx.data_dir):
        r = detector.detect(lot_id, ctx.data_dir)
        lots.append({"lot_id": lot_id, "flagged": r.flagged, "breached_params": r.breached_params})
    return {"lots": lots}


@app.get("/lot/{lot_id}")
def get_lot(lot_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        return gls_run.run(lot_id, data_dir=ctx.data_dir)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"lot {lot_id} not found")


@app.get("/disposition/{lot_id}")
def get_disposition(lot_id: str, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        return _disposition_payload(lot_id, ctx)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"lot {lot_id} not found")


@app.post("/approve")
def approve(req: ApproveReq, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        disp = detector.decide(detector.detect(req.lot_id, ctx.data_dir))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"lot {req.lot_id} not found")
    try:
        return shell.approve(req.lot_id, disp, approved_by=req.approved_by,
                             rationale=req.rationale, memory_dir=ctx.memory_dir)
    except shell.DispositionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/override")
def override(req: OverrideReq, ctx: AppContext = Depends(get_ctx)) -> dict:
    try:
        return shell.override(req.lot_id, req.decision, approved_by=req.approved_by,
                              reason=req.reason, rationale=req.rationale, memory_dir=ctx.memory_dir)
    except shell.DispositionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/ask")
def ask(req: AskReq, ctx: AppContext = Depends(get_ctx)) -> dict:
    res = agent.ask(req.lot_id, req.question, model=ctx.ask_model, data_dir=ctx.data_dir,
                    persist_dir=ctx.persist_dir, embedder=ctx.embedder)
    return {"answer": res.answer, "trace": res.trace}
