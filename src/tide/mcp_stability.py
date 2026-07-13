from __future__ import annotations

from typing import Any

from . import core as tide_core
from . import mcp
from . import mcp_model_policy as _policy_adapter
from .project import project_root
from .stability import ensure_commit_hook

_ORIGINAL_TOOLS = mcp.tools
_ORIGINAL_CALL_TOOL = mcp.call_tool
_ORIGINAL_SUMMARY = mcp._tool_summary

_INSTRUCTIONS = """
Before every git commit, call commit_check. A user request to commit authorizes the Git action but never bypasses validation, independent review, hardgates, or fingerprint checks.
Never use git commit --no-verify to bypass the Tide pre-commit hook.
If commit_check returns allowed=false and agent_should_continue=true, continue the exact next_action and do not end the turn.
When a verified code defect is reported after approval and edits are required, call reopen with code_change_required=true. Let authorize create the client permission prompt for closure_reopen before editing.
""".strip()


def tools() -> list[dict[str, Any]]:
    surface = list(_ORIGINAL_TOOLS())
    for index, tool in enumerate(surface):
        if tool.get("name") == "reopen":
            updated = dict(tool)
            schema = dict(updated.get("inputSchema") or {})
            properties = dict(schema.get("properties") or {})
            properties["code_change_required"] = {
                "type": "boolean",
                "default": False,
                "description": "True only when an approved task has a verified code defect that requires new edits.",
            }
            schema["properties"] = properties
            updated["inputSchema"] = schema
            surface[index] = updated
            break
    commit_tool = {
        "name": "commit_check",
        "description": "Required gate before git commit. Verifies current approval, validation, hardgates, fingerprint, and staged files.",
        "inputSchema": mcp._schema(),
    }
    check_index = next(
        (index for index, tool in enumerate(surface) if tool.get("name") == "check"),
        len(surface) - 1,
    )
    surface.insert(check_index + 1, commit_tool)
    return surface


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    root = project_root()
    if name == "commit_check":
        return tide_core.commit_check(root)
    if name == "reopen" and bool(arguments.get("code_change_required", False)):
        value = tide_core.reopen(
            root,
            reason=str(arguments["reason"]),
            code_change_required=True,
        )
        return _policy_adapter._attach(value, phase="correction")

    value = _ORIGINAL_CALL_TOOL(name, arguments)
    if name in {"prepare", "resume"}:
        hook = ensure_commit_hook(root)
        if isinstance(value, dict):
            value = {**value, "commit_hook": hook}
    return value


def tool_summary(name: str, value: Any) -> str:
    if name == "commit_check" and isinstance(value, dict):
        state = "allowed" if value.get("allowed") else "blocked"
        blocker = (value.get("blockers") or [None])[0]
        return f"commit_check: {state}; blocker={blocker or 'none'}; next={value.get('next_action')}"
    return _ORIGINAL_SUMMARY(name, value)


def install() -> None:
    if _INSTRUCTIONS not in mcp.INSTRUCTIONS:
        mcp.INSTRUCTIONS = mcp.INSTRUCTIONS.rstrip() + "\n" + _INSTRUCTIONS
    mcp.tools = tools
    mcp.call_tool = call_tool
    mcp._tool_summary = tool_summary
