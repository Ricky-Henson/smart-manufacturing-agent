"""MCP server smoke test — skipped if the optional `mcp` SDK isn't installed."""
import asyncio

import pytest

pytest.importorskip("mcp")

from mcp_server import server  # noqa: E402


def test_read_only_tools_registered():
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"list_lots", "get_lot_stats", "detect_lot", "retrieve_sop"} <= names


def test_all_tools_are_read_only():
    tools = asyncio.run(server.mcp.list_tools())
    assert all(t.annotations and t.annotations.readOnlyHint for t in tools)
