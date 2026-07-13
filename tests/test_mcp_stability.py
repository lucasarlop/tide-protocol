from __future__ import annotations

from tide import mcp


def test_mcp_exposes_commit_gate_and_explicit_code_reopen() -> None:
    tools = {tool["name"]: tool for tool in mcp.tools()}

    assert "commit_check" in tools
    assert tools["commit_check"]["inputSchema"]["properties"] == {}
    reopen = tools["reopen"]["inputSchema"]["properties"]
    assert reopen["code_change_required"]["type"] == "boolean"
    assert reopen["code_change_required"]["default"] is False
