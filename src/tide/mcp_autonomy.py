from __future__ import annotations

from typing import Any

from . import mcp
from .autonomy import enrich
from .project import project_root

_ORIGINAL_CALL_TOOL = mcp.call_tool
_ORIGINAL_SUMMARY = mcp._tool_summary

_AUTONOMY_INSTRUCTIONS = """
Validation, review, blocker correction, and local operational verification are autonomous work. Never end a turn merely because one of them remains.
When a Tide result contains authorization_request, call authorize with exactly those gates. The client permission prompt is the user interaction; do not replace it with a vague prose request.
Only stop for user input when user_action_required=true, the user denies the permission prompt, a genuine requirement choice remains, or an external dependency makes progress impossible.
When agent_should_continue=true, continue to the exact next_action before producing a final response.
""".strip()

_ENRICHED_TOOLS = {
    "prepare",
    "revise",
    "split",
    "reopen",
    "authorize",
    "check",
    "resume",
    "handoff",
    "status",
}


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    value = _ORIGINAL_CALL_TOOL(name, arguments)
    if name in _ENRICHED_TOOLS:
        return enrich(project_root(), value)
    return value


def tool_summary(name: str, value: Any) -> str:
    base = _ORIGINAL_SUMMARY(name, value)
    if not isinstance(value, dict) or name not in _ENRICHED_TOOLS:
        return base
    if value.get("user_action_required"):
        request = value.get("authorization_request") or {}
        arguments = request.get("arguments") if isinstance(request, dict) else {}
        gates = arguments.get("gates") if isinstance(arguments, dict) else []
        return f"{base}; authorization_required={','.join(str(gate) for gate in gates)}"
    if value.get("agent_should_continue"):
        return f"{base}; continue=true"
    return base


def install() -> None:
    if _AUTONOMY_INSTRUCTIONS not in mcp.INSTRUCTIONS:
        mcp.INSTRUCTIONS = mcp.INSTRUCTIONS.rstrip() + "\n" + _AUTONOMY_INSTRUCTIONS
    mcp.call_tool = call_tool
    mcp._tool_summary = tool_summary
