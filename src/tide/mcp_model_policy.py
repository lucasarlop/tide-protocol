from __future__ import annotations

from typing import Any

from . import mcp
from .core import model_policy
from .project import project_root

_ORIGINAL_TOOLS = mcp.tools
_ORIGINAL_CALL_TOOL = mcp.call_tool
_ORIGINAL_SUMMARY = mcp._tool_summary
_ORIGINAL_HANDLE = mcp.handle

INSTRUCTIONS = """Tide 1.1 keeps code work autonomous, bounded, concise, resumable, and proportionate in model cost.
Call prepare before editing and check before completion.
Call model_policy at task start and major phase boundaries. Treat it as deterministic guidance, not permission to switch models on every tool call.
Apply writer-model changes only in a fresh session or at a real planning, implementation, correction, or investigation boundary. Keep the current writer for validation, operational checks, and closure.
Use the reviewer_agent returned by model_policy or review_packet. Ordinary incremental review uses the balanced reviewer; full or sensitive review uses the critical reviewer.
Never escalate to xhigh merely because a task is long, has many files, or consumed time. Xhigh requires an explicitly unknown root cause after at least two bounded failed attempts.
Use trusted autonomy: continue routine reads, edits, targeted tests, blocker fixes, split, local rebuilds, and health checks without asking permission. Ask one concise question only for a real requirement choice, destructive data change, production action, external cost, or an irreversible Git action not already authorized.
Use targeted validations while implementing. Run final validation once per fingerprint; Tide reuses current final evidence automatically.
Use background validation plus validation_wait. Never run shell sleep for polling.
Reviews are incremental after the first compatible review. An approved fingerprint is immutable and cannot be reviewed again without a real code or boundary change.
Use operational_verify for rebuild, restart, health, worker, queue, and smoke checks. Operational checks never reopen code review.
Use split for a smaller child segment. Approved parent segments become receipts and do not need external acknowledgements.
Findings need stable id, severity, message, paths, and expected_action. Only blocking findings stay in the task.
Tide keeps a compact resume checkpoint automatically. Use resume in a fresh session; handoff is an optional explicit snapshot.
Communicate in professional Caveman-lite style: no filler, no routine tool narration, no raw log dumps. Keep code, commands, paths, model names, and error strings exact. Use normal prose for risk, ambiguity, model escalation, and irreversible actions.
Never commit, push, merge, deploy, or delete data without explicit or prior user authorization."""


def _policy_schema() -> dict[str, Any]:
    return mcp._schema(
        {
            "phase": {
                "type": "string",
                "enum": [
                    "planning",
                    "exploration",
                    "implementation",
                    "correction",
                    "investigation",
                    "validation",
                    "review",
                    "operational",
                    "closure",
                ],
            },
            "strategy": {
                "type": "string",
                "enum": ["economy", "balanced", "quality", "manual"],
            },
            "review_mode": {
                "type": "string",
                "enum": ["incremental", "full"],
            },
            "failed_attempts": {"type": "integer", "minimum": 0},
            "root_cause_known": {"type": "boolean"},
        }
    )


def tools() -> list[dict[str, Any]]:
    surface = list(_ORIGINAL_TOOLS())
    surface.insert(
        6,
        {
            "name": "model_policy",
            "description": (
                "Recommend a deterministic model and reasoning profile for the current "
                "phase. Does not silently switch the active writer."
            ),
            "inputSchema": _policy_schema(),
        },
    )
    for index, tool in enumerate(surface):
        if tool["name"] == "review_packet":
            updated = dict(tool)
            updated["description"] = (
                "Create or reuse a review packet and return the correct reviewer agent."
            )
            surface[index] = updated
            break
    return surface


def _policy(
    arguments: dict[str, Any] | None = None,
    *,
    phase: str | None = None,
    review_mode: str | None = None,
) -> dict[str, Any]:
    arguments = arguments or {}
    return model_policy(
        project_root(),
        phase=phase or (str(arguments.get("phase") or "") or None),
        strategy=str(arguments.get("strategy") or "") or None,
        review_mode=review_mode or (str(arguments.get("review_mode") or "") or None),
        failed_attempts=(
            int(arguments["failed_attempts"])
            if arguments.get("failed_attempts") is not None
            else None
        ),
        root_cause_known=(
            bool(arguments["root_cause_known"])
            if arguments.get("root_cause_known") is not None
            else None
        ),
    )


def _attach(
    value: Any,
    *,
    phase: str | None = None,
    review_mode: str | None = None,
) -> Any:
    if not isinstance(value, dict):
        return value
    return {
        **value,
        "model_policy": _policy(phase=phase, review_mode=review_mode),
    }


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "model_policy":
        return _policy(arguments)

    value = _ORIGINAL_CALL_TOOL(name, arguments)
    phases = {
        "prepare": "planning",
        "revise": "implementation",
        "split": "implementation",
    }
    if name == "reopen" and isinstance(value, dict):
        phase = (
            "operational"
            if value.get("lifecycle") == "operational_verification"
            else "correction"
        )
        return _attach(value, phase=phase)
    if name == "review_packet":
        review_mode = (
            str(value.get("review_mode"))
            if isinstance(value, dict)
            and value.get("review_mode") in {"full", "incremental"}
            else ("full" if bool(arguments.get("full", False)) else "incremental")
        )
        enriched = _attach(value, phase="review", review_mode=review_mode)
        if isinstance(enriched, dict):
            policy = enriched.get("model_policy") or {}
            enriched["reviewer_agent"] = policy.get("reviewer_agent")
        return enriched
    if name == "check" and isinstance(value, dict):
        blocker = str(value.get("primary_blocker") or "").lower()
        if value.get("ready"):
            phase = "closure"
        elif "review" in blocker:
            phase = "review"
        elif "validation" in blocker:
            phase = "validation"
        else:
            phase = "correction"
        return _attach(value, phase=phase)
    if name in {"resume", "handoff", "status"}:
        return _attach(value)
    if name in phases:
        return _attach(value, phase=phases[name])
    return value


def _policy_summary(value: dict[str, Any]) -> str:
    policy = (
        value.get("model_policy")
        if isinstance(value.get("model_policy"), dict)
        else value
    )
    recommendation = (
        policy.get("recommendation")
        if isinstance(policy.get("recommendation"), dict)
        else {}
    )
    if not recommendation:
        return "model=manual"
    return (
        f"model={recommendation.get('model')}; "
        f"reasoning={recommendation.get('reasoning_effort')}; "
        f"switch={str(bool(recommendation.get('switch_recommended'))).lower()}"
    )


def tool_summary(name: str, value: Any) -> str:
    if not isinstance(value, dict):
        return _ORIGINAL_SUMMARY(name, value)
    if name == "model_policy":
        return (
            f"model_policy: phase={value.get('phase')}; {_policy_summary(value)}; "
            f"reviewer={value.get('reviewer_agent') or 'none'}"
        )
    if name == "review_packet":
        base = _ORIGINAL_SUMMARY(name, value)
        return f"{base}; reviewer={value.get('reviewer_agent') or 'none'}"
    base = _ORIGINAL_SUMMARY(name, value)
    if isinstance(value.get("model_policy"), dict):
        return f"{base}; {_policy_summary(value)}"
    return base


def handle(request: dict[str, Any]) -> None:
    if request.get("method") == "initialize":
        mcp.respond(
            request.get("id"),
            result={
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "tide", "version": "1.1.0"},
                "instructions": INSTRUCTIONS,
            },
        )
        return
    _ORIGINAL_HANDLE(request)


def install() -> None:
    mcp.INSTRUCTIONS = INSTRUCTIONS
    mcp.tools = tools
    mcp.call_tool = call_tool
    mcp._tool_summary = tool_summary
    mcp.handle = handle
