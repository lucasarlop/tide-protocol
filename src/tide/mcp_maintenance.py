from __future__ import annotations

from typing import Any

from . import mcp

_ORIGINAL_CALL_TOOL = mcp.call_tool
_ORIGINAL_SUMMARY = mcp._tool_summary
_ORIGINAL_HANDLE = mcp.handle


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    value = _ORIGINAL_CALL_TOOL(name, arguments)
    if name == "lock_list" and isinstance(value, list):
        return {"locks": value, "count": len(value)}
    return value


def tool_summary(name: str, value: Any) -> str:
    if name == "lock_list" and isinstance(value, dict):
        return f"lock_list: {int(value.get('count', 0))} lock(s)"
    return _ORIGINAL_SUMMARY(name, value)


def handle(request: dict[str, Any]) -> None:
    if request.get("method") == "initialize":
        mcp.respond(
            request.get("id"),
            result={
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "tide", "version": "1.1.1"},
                "instructions": mcp.INSTRUCTIONS,
            },
        )
        return
    _ORIGINAL_HANDLE(request)


def install() -> None:
    mcp.call_tool = call_tool
    mcp._tool_summary = tool_summary
    mcp.handle = handle
