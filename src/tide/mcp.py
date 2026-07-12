from __future__ import annotations

import json
import sys
from typing import Any
from urllib.parse import urlparse

from .artifacts import list_review_resources
from .context import query_context
from .core import (
    authorize,
    check,
    create_review_packet,
    external_acknowledge,
    get_review_packet,
    handoff,
    operational_verify,
    prepare,
    preparation_report,
    record_validation,
    reopen,
    resume,
    revise,
    split,
    start_validation,
    submit_review,
    validation_log,
    validation_status,
    validation_wait,
)
from .locks import load_locks, render_draft
from .project import TideError, project_root

INSTRUCTIONS = """Tide 1.0 keeps code work autonomous, bounded, concise, and resumable.
Call prepare before editing and check before completion.
Use trusted autonomy: continue routine reads, edits, targeted tests, blocker fixes, split, local rebuilds, and health checks without asking permission. Ask one concise question only for a real requirement choice, destructive data change, production action, external cost, or an irreversible Git action not already authorized.
Use targeted validations while implementing. Run final validation once per fingerprint; Tide reuses current final evidence automatically.
Use background validation plus validation_wait. Never run shell sleep for polling.
Reviews are incremental after the first compatible review. An approved fingerprint is immutable and cannot be reviewed again without a real code or boundary change.
Use operational_verify for rebuild, restart, health, worker, queue, and smoke checks. Operational checks never reopen code review.
Use split for a smaller child segment. Approved parent segments become receipts and do not need external acknowledgements.
Findings need stable id, severity, message, paths, and expected_action. Only blocking findings stay in the task.
Tide keeps a compact resume checkpoint automatically. Use resume in a fresh session; handoff is an optional explicit snapshot.
Communicate in professional Caveman-lite style: no filler, no routine tool narration, no raw log dumps. Keep code, commands, paths, and error strings exact. Use normal prose for risk, ambiguity, and irreversible actions.
Never commit, push, merge, deploy, or delete data without explicit or prior user authorization."""


def _schema(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "object", "properties": properties or {}, "additionalProperties": False}
    if required:
        value["required"] = required
    return value


def _finding_schema() -> dict[str, Any]:
    return {
        "oneOf": [
            {"type": "string"},
            {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "severity": {"type": "string", "enum": ["blocking", "follow_up", "info"]},
                    "message": {"type": "string"},
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "expected_action": {"type": "string"},
                },
                "required": ["id", "severity", "message"],
                "additionalProperties": False,
            },
        ]
    }


def tools() -> list[dict[str, Any]]:
    return [
        {"name": "prepare", "description": "Prepare a bounded change.", "inputSchema": _schema({"task": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}, "required_validations": {"type": "array", "items": {"type": "string"}}}, ["task"])},
        {"name": "revise", "description": "Revise inside the current segment without resetting its budget.", "inputSchema": _schema({"task": {"type": "string"}, "add_files": {"type": "array", "items": {"type": "string"}}, "remove_files": {"type": "array", "items": {"type": "string"}}, "add_required_validations": {"type": "array", "items": {"type": "string"}}, "remove_required_validations": {"type": "array", "items": {"type": "string"}}})},
        {"name": "split", "description": "Create a smaller child segment and retain approved parent receipts.", "inputSchema": _schema({"task": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}}, ["task", "files"])},
        {"name": "reopen", "description": "Reopen for a concrete new code defect. Unchanged approved code enters operational verification instead.", "inputSchema": _schema({"reason": {"type": "string"}}, ["reason"])},
        {"name": "external_acknowledge", "description": "Acknowledge genuinely external stable worktree changes.", "inputSchema": _schema({"files": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}}, ["files", "reason"])},
        {"name": "authorize", "description": "Record explicit authorization only for a genuine user decision gate.", "inputSchema": _schema({"gates": {"type": "array", "items": {"type": "string"}}, "all": {"type": "boolean", "default": False}})},
        {"name": "context", "description": "Return direct live-code context when relevant.", "inputSchema": _schema({"query": {"type": "string"}}, ["query"])},
        {"name": "check", "description": "Run the deterministic closure gate.", "inputSchema": _schema()},
        {"name": "validate", "description": "Run targeted or final validation with scoped coverage.", "inputSchema": _schema({"command": {"type": "array", "items": {"type": "string"}}, "timeout": {"type": "integer", "minimum": 1}, "background": {"type": "boolean", "default": False}, "covers": {"type": "array", "items": {"type": "string"}}, "phase": {"type": "string", "enum": ["targeted", "final"], "default": "targeted"}}, ["command"])},
        {"name": "validation_status", "description": "Read background validation status without waiting.", "inputSchema": _schema({"validation_id": {"type": "string"}}, ["validation_id"])},
        {"name": "validation_wait", "description": "Wait inside Tide for a background validation. Do not use shell sleep.", "inputSchema": _schema({"validation_id": {"type": "string"}, "wait_seconds": {"type": "integer", "minimum": 1, "maximum": 60, "default": 20}}, ["validation_id"])},
        {"name": "validation_log", "description": "Read a saved validation log only when compact evidence is insufficient.", "inputSchema": _schema({"log_id": {"type": "string"}}, ["log_id"])},
        {"name": "review_packet", "description": "Create or reuse a validated incremental review packet.", "inputSchema": _schema({"full": {"type": "boolean", "default": False}, "full_reason": {"type": "string"}})},
        {"name": "review_get", "description": "Read a review packet and submission token.", "inputSchema": _schema({"review_id": {"type": "string"}}, ["review_id"])},
        {"name": "review_submit", "description": "Submit verdict with complete structured findings.", "inputSchema": _schema({"review_id": {"type": "string"}, "submission_token": {"type": "string"}, "approved": {"type": "boolean"}, "findings": {"type": "array", "items": _finding_schema()}}, ["review_id", "submission_token", "approved"])},
        {"name": "operational_verify", "description": "Record rebuild, restart, health, queue, worker, or smoke checks without reopening review.", "inputSchema": _schema({"name": {"type": "string"}, "passed": {"type": "boolean"}, "details": {"type": "string"}}, ["name", "passed"])},
        {"name": "resume", "description": "Load the compact current checkpoint in a fresh session.", "inputSchema": _schema()},
        {"name": "handoff", "description": "Return an explicit compact checkpoint for another session or agent.", "inputSchema": _schema()},
        {"name": "lock_list", "description": "List Module Locks.", "inputSchema": _schema()},
        {"name": "lock_template", "description": "Generate a Module Lock draft.", "inputSchema": _schema({"scope": {"type": "string"}, "name": {"type": "string"}, "criticality": {"type": "string", "default": "production"}}, ["scope", "name"])},
        {"name": "status", "description": "Show compact lifecycle, evidence, blockers, receipts, and next action.", "inputSchema": _schema()},
    ]


def _tool_schema(name: str) -> dict[str, Any]:
    for tool in tools():
        if tool["name"] == name:
            return tool["inputSchema"]
    raise TideError(f"unknown tool: {name}")


def _validate_arguments(name: str, arguments: dict[str, Any]) -> None:
    schema = _tool_schema(name)
    unknown = sorted(set(arguments) - set(schema.get("properties", {})))
    if unknown:
        raise TideError(f"unknown arguments for {name}: {', '.join(unknown)}")
    missing = [key for key in schema.get("required", []) if key not in arguments]
    if missing:
        raise TideError(f"missing arguments for {name}: {', '.join(missing)}")


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    _validate_arguments(name, arguments)
    root = project_root()
    if name == "prepare":
        return prepare(root, str(arguments["task"]), list(arguments.get("files") or []), list(arguments.get("required_validations") or []))
    if name == "revise":
        return revise(root, task=str(arguments["task"]) if arguments.get("task") is not None else None, add_files=list(arguments.get("add_files") or []), remove_files=list(arguments.get("remove_files") or []), add_required_validations=list(arguments.get("add_required_validations") or []), remove_required_validations=list(arguments.get("remove_required_validations") or []))
    if name == "split":
        return split(root, task=str(arguments["task"]), files=list(arguments["files"]))
    if name == "reopen":
        return reopen(root, reason=str(arguments["reason"]))
    if name == "external_acknowledge":
        return external_acknowledge(root, list(arguments["files"]), reason=str(arguments["reason"]))
    if name == "authorize":
        return authorize(root, list(arguments.get("gates") or []), all_gates=bool(arguments.get("all", False)))
    if name == "context":
        return query_context(root, str(arguments["query"]))
    if name == "check":
        return check(root)
    if name == "validate":
        command = list(arguments["command"])
        timeout = int(arguments.get("timeout", 300))
        covers = list(arguments.get("covers") or [])
        phase = str(arguments.get("phase") or "targeted")
        if bool(arguments.get("background", False)):
            return start_validation(root, command, timeout, covers=covers, phase=phase)
        return record_validation(root, command, timeout, covers=covers, phase=phase)
    if name == "validation_status":
        return validation_status(root, str(arguments["validation_id"]))
    if name == "validation_wait":
        return validation_wait(root, str(arguments["validation_id"]), int(arguments.get("wait_seconds", 20)))
    if name == "validation_log":
        return validation_log(root, str(arguments["log_id"]))
    if name == "review_packet":
        return create_review_packet(root, full=bool(arguments.get("full", False)), full_reason=str(arguments.get("full_reason") or "") or None)
    if name == "review_get":
        return get_review_packet(root, str(arguments["review_id"]))
    if name == "review_submit":
        return submit_review(root, review_id=str(arguments["review_id"]), submission_token=str(arguments["submission_token"]), approved=bool(arguments["approved"]), findings=list(arguments.get("findings") or []))
    if name == "operational_verify":
        return operational_verify(root, name=str(arguments["name"]), passed=bool(arguments["passed"]), details=str(arguments.get("details") or ""))
    if name == "resume":
        return resume(root)
    if name == "handoff":
        return handoff(root)
    if name == "lock_list":
        return [{"name": lock.name, "file": str(lock.file.relative_to(root)), "paths": list(lock.paths), "criticality": lock.criticality, "review_required": lock.review_required} for lock in load_locks(root)]
    if name == "lock_template":
        return {"content": render_draft(name=str(arguments["name"]), scope=str(arguments["scope"]), criticality=str(arguments.get("criticality", "production")))}
    if name == "status":
        return preparation_report(root)
    raise TideError(f"unknown tool: {name}")


def _brief(values: list[Any] | None, limit: int = 2) -> str:
    items = [str(value) for value in (values or []) if str(value)]
    if not items:
        return "none"
    return "; ".join(items[:limit]) + (f" (+{len(items)-limit})" if len(items) > limit else "")


def _tool_summary(name: str, value: Any) -> str:
    if not isinstance(value, dict):
        return f"{name}: completed"
    if name in {"prepare", "revise", "split", "reopen", "status"}:
        resume_value = value.get("resume") if isinstance(value.get("resume"), dict) else {}
        return f"{name}: segment={value.get('segment_index', resume_value.get('segment'))}; lifecycle={value.get('lifecycle')}; split={bool(value.get('split_required'))}; next={resume_value.get('next_action') or value.get('next_action')}"
    if name == "validate":
        if value.get("reused"):
            return f"validate: reused current {value.get('phase')} evidence"
        if value.get("status") in {"starting", "running"}:
            return f"validate: running as {value.get('validation_id')}"
        return f"validate: {'passed' if value.get('passed') else 'failed'}; phase={value.get('phase')}; log={value.get('log_id', 'pending')}"
    if name in {"validation_status", "validation_wait"}:
        passed = value.get("passed")
        return f"{name}: {value.get('status')}; passed={'pending' if passed is None else str(bool(passed)).lower()}"
    if name == "review_packet":
        return f"review_packet: {value.get('review_id')}; mode={value.get('review_mode')}; files={len(value.get('files') or [])}; reused={bool(value.get('reused'))}"
    if name == "review_submit":
        return f"review_submit: {'approved' if value.get('approved') else 'blocked'}; blocking={len(value.get('blocking_findings') or [])}; follow_up={len(value.get('follow_up_findings') or [])}"
    if name == "check":
        return f"check: {'ready' if value.get('ready') else 'blocked'}; lifecycle={value.get('lifecycle')}; blocker={value.get('primary_blocker') or 'none'}; next={value.get('next_action')}"
    if name in {"resume", "handoff"}:
        return f"{name}: segment={value.get('segment')}; lifecycle={value.get('lifecycle')}; blockers={len((value.get('review') or {}).get('blocking') or [])}; next={value.get('next_action')}"
    if name == "operational_verify":
        return f"operational_verify: {value.get('name')}; passed={bool(value.get('passed'))}"
    if name == "external_acknowledge":
        return f"external_acknowledge: {len(value.get('acknowledged') or [])} file(s)"
    if name == "validation_log":
        return f"validation_log: {value.get('log_id')}"
    return f"{name}: completed"


def respond(request_id: Any, *, result: Any = None, error: str | None = None) -> None:
    if request_id is None:
        return
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    payload["error" if error else "result"] = {"code": -32000, "message": error} if error else result
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def handle(request: dict[str, Any]) -> None:
    request_id = request.get("id")
    method = request.get("method")
    if method == "initialize":
        respond(request_id, result={"protocolVersion": "2025-03-26", "capabilities": {"tools": {}, "resources": {}}, "serverInfo": {"name": "tide", "version": "1.0.0"}, "instructions": INSTRUCTIONS})
        return
    if method == "tools/list":
        respond(request_id, result={"tools": tools()})
        return
    if method == "tools/call":
        params = request.get("params") or {}
        try:
            name = str(params.get("name"))
            value = call_tool(name, dict(params.get("arguments") or {}))
            respond(request_id, result={"content": [{"type": "text", "text": _tool_summary(name, value)}], "structuredContent": value, "isError": False})
        except Exception as exc:
            respond(request_id, result={"content": [{"type": "text", "text": str(exc)}], "isError": True})
        return
    if method == "resources/list":
        try:
            respond(request_id, result={"resources": list_review_resources(project_root())})
        except Exception as exc:
            respond(request_id, error=str(exc))
        return
    if method == "resources/read":
        try:
            uri = str((request.get("params") or {}).get("uri", ""))
            parsed = urlparse(uri)
            if parsed.scheme != "tide" or parsed.netloc != "reviews" or not parsed.path.strip("/"):
                raise TideError(f"unknown resource: {uri}")
            review_id = parsed.path.strip("/")
            packet = get_review_packet(project_root(), review_id)
            respond(request_id, result={"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(packet, indent=2, ensure_ascii=False)}]})
        except Exception as exc:
            respond(request_id, error=str(exc))
        return
    if method == "ping":
        respond(request_id, result={})
        return
    respond(request_id, error=f"unknown method: {method}")


def serve() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            handle(json.loads(line))
        except Exception as exc:
            respond(None, error=str(exc))
    return 0
