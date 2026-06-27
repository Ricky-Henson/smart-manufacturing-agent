"""Optional MCP server exposing the agent's read-only manufacturing tools.

Separate from the core (install `requirements-mcp.txt` to use it). It reuses the
same deterministic, already-verified functions as `agent_core`, so an MCP client
calls exactly the logic the in-process /ask loop calls.
"""
