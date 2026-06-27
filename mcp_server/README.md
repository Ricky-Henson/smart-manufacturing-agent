# MCP server (optional)

Exposes the probe lot-disposition agent's **read-only** tools over the Model
Context Protocol, so any MCP client (e.g. Claude Desktop) can call them. It is a
thin wrapper over the same deterministic, already-tested `agent_core` functions —
one source of truth for the logic.

## Tools (all read-only)
| Tool | Returns |
|---|---|
| `list_lots` | available lot ids |
| `get_lot_stats(lot_id)` | per-parameter stats (mean/std/min/max/limit/n_breach) |
| `detect_lot(lot_id)` | deterministic detection: flagged + breached params + detail |
| `retrieve_sop(query, k=4)` | cited governing SOP clause(s) |

No `approve`/`override` (actions) are exposed — consistent with the
deterministic-shell principle: the model can read, never act.

## Run
```bash
pip install -r requirements-mcp.txt
# the lot tools need generated data + a built index first:
python -m scripts.generate_data && python -m scripts.build_index
python -m mcp_server.server          # stdio
```

## Register with an MCP client (Claude Desktop example)
```json
{
  "mcpServers": {
    "smart-mfg": {
      "command": "/abs/path/.venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/abs/path/smart-manufacturing-agent"
    }
  }
}
```

## Why MCP here (vs the internal tool loop)
The `/ask` loop already does MCP-*style* tool calls in-process. This server makes
the same tools callable by *external* MCP clients — useful for composing the
manufacturing tools with other tools, or driving them from a desktop agent. The
project does **not** require MCP to function; it's an integration surface.
