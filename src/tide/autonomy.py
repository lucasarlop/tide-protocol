from __future__ import annotations

from pathlib import Path
from typing import Any

from .project import load_runtime


def _pending_hardgates(root: Path, value: dict[str, Any]) -> list[str]:
    explicit = value.get("pending_hardgates")
    if isinstance(explicit, list):
        return sorted({str(gate) for gate in explicit if str(gate)})
    runtime = load_runtime(root)
    hardgates = {str(gate) for gate in runtime.get("hardgates", []) if str(gate)}
    authorized = {
        str(gate) for gate in runtime.get("authorized_hardgates", []) if str(gate)
    }
    return sorted(hardgates - authorized)


def enrich(root: Path, value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    pending = _pending_hardgates(root, value)
    ready = bool(value.get("ready")) or value.get("status") == "ready"
    user_action_required = bool(pending)
    agent_should_continue = not ready and not user_action_required
    request = (
        {
            "tool": "authorize",
            "arguments": {"gates": pending, "all": False},
            "interaction": "client_permission_prompt",
            "message": "Authorize the pending Tide hardgates.",
        }
        if pending
        else None
    )
    result = {
        **value,
        "user_action_required": user_action_required,
        "agent_should_continue": agent_should_continue,
        "authorization_request": request,
    }
    if pending:
        result["next_action"] = (
            "call authorize with the pending hardgates; let the client request user approval"
        )
    nested = result.get("resume")
    if isinstance(nested, dict):
        nested = {
            **nested,
            "user_action_required": user_action_required,
            "agent_should_continue": agent_should_continue,
            "authorization_request": request,
        }
        if pending:
            nested["next_action"] = result["next_action"]
        result["resume"] = nested
    return result
