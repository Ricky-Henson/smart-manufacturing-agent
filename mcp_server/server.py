"""MCP server (stdio) exposing the probe lot-disposition agent's READ-ONLY tools.

Why this exists: the agent already uses MCP-*style* tool calls internally. This
turns the same tools into a real **MCP** server, so any MCP client (e.g. Claude
Desktop) can call them. It reuses the same deterministic, already-tested
functions as `agent_core` — so the MCP tools inherit the verification, and there
is exactly one source of truth for the logic.

Read-only by design: NO approve/override (actions) are exposed. Consistent with
the deterministic-shell principle — the model can read, never act. Local stdio
transport fits the offline, no-cloud design.

Run:    python -m mcp_server.server
Needs:  pip install -r requirements-mcp.txt, plus generated data + a built SOP
        index (scripts.generate_data / scripts.build_index) for the lot tools.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from agent_core import detector, ingest, rag
from agent_core.skills.get_lot_stats import run as gls_run

mcp = FastMCP("smart-mfg")

# Every tool here is non-destructive and reads local data only.
_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


@mcp.tool(annotations=_READ_ONLY)
def list_lots() -> list[str]:
    """List the available wafer probe lot ids (from the configured data root)."""
    return ingest.list_lots()


@mcp.tool(annotations=_READ_ONLY)
def get_lot_stats(lot_id: str) -> dict:
    """Parametric summary stats (mean/std/min/max/limit/n_breach per parameter) for one lot."""
    return gls_run.run(lot_id)


@mcp.tool(annotations=_READ_ONLY)
def detect_lot(lot_id: str) -> dict:
    """Run DETERMINISTIC anomaly detection on a lot: flagged + breached parameters + detail. No LLM."""
    return detector.detect(lot_id).to_dict()


@mcp.tool(annotations=_READ_ONLY)
def retrieve_sop(query: str, k: int = 4) -> list[dict]:
    """Retrieve the governing QC-SOP clause(s) for a query (e.g. breached parameters), cited."""
    return [{"cite_id": c.cite_id, "source": c.source, "text": c.text}
            for c in rag.retrieve(query, k=k)]


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
