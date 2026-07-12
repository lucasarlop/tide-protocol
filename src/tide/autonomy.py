from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .project import load_runtime

_ORIGINALS: dict[str, Callable[..., Any]] = {}


def install(core: ModuleType) -> None:
    if getattr(core, "_autonomy_boundary_installed", False):
        return
    for name in ("preparation_report", "check", "resume", "handoff"):
        _ORIGINALS[name] = getattr(core, name)
    core.preparation_report = preparation_report
    core.check = check
    core.resume = resume
    core.handoff = handoff
    core._autonomy_boundary_installed = True


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


def _enrich(root: Path, value: Any) -> Any:
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


def preparation_report(root: Path, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    return _enrich(root, _ORIGINALS["preparation_report"](root, runtime))


def check(root: Path) -> dict[str, Any]:
    return _enrich(root, _ORIGINALS["check"](root))


def resume(root: Path) -> dict[str, Any]:
    return _enrich(root, _ORIGINALS["resume"](root))


def handoff(root: Path) -> dict[str, Any]:
    return _enrich(root, _ORIGINALS["handoff"](root))
