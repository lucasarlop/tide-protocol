from __future__ import annotations

import json
import sys
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .artifacts import list_review_resources, read_review_packet
from .core import (
    abandon,
    authorize,
    check,
    commit_check,
    convergence,
    create_review_packet,
    external_acknowledge,
    get_review_packet,
    handoff,
    operational_verify,
    prepare,
    reopen,
    resume,
    revise,
    split,
    start_validation,
    submit_review,
    validation_log,
    validation_status,
    validation_wait,
    record_validation,
)
from .model_policy import model_policy
from .project import TideError, project_root
from .protocol import WRITER_INSTRUCTIONS

INSTRUCTIONS = WRITER_INSTRUCTIONS


def _schema(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "object", "properties": properties or {}, "additionalProperties": False}
    if required:
        value["required"] = required
    return value


def _finding_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "severity": {"type": "string", "enum": ["blocking", "follow_up", "info"]},
            "message": {"type": "string"},
            "paths": {"type": "array", "items": {"type": "string"}},
            "expected_action": {"type": "string"},
        },
        "required": ["id", "severity", "message", "paths", "expected_action"],
        "additionalProperties": False,
    }


def tools() -> list[dict[str, Any]]:
    return [
        {"name": "resume", "description": "Load the current task checkpoint. Call first in every new agent session.", "inputSchema": _schema()},
        {"name": "prepare", "description": "Prepare a new bounded task only when no active task exists.", "inputSchema": _schema({"task": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}, "required_validations": {"type": "array", "items": {"type": "string"}}}, ["task"])},
        {"name": "revise", "description": "Adjust the current task boundary or validation plan while preserving current evidence.", "inputSchema": _schema({"task": {"type": "string"}, "add_files": {"type": "array", "items": {"type": "string"}}, "remove_files": {"type": "array", "items": {"type": "string"}}, "add_required_validations": {"type": "array", "items": {"type": "string"}}, "remove_required_validations": {"type": "array", "items": {"type": "string"}}})},
        {"name": "split", "description": "Optionally narrow a non-converging task to a smaller child segment.", "inputSchema": _schema({"task": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}}, ["task", "files"])},
        {"name": "reopen", "description": "Reopen approved work for a verified defect or enter operational verification.", "inputSchema": _schema({"reason": {"type": "string"}, "code_change_required": {"type": "boolean", "default": False}}, ["reason"])},
        {"name": "validate", "description": "Run targeted or final validation with explicit file coverage.", "inputSchema": _schema({"command": {"type": "array", "items": {"type": "string"}}, "timeout": {"type": "integer", "minimum": 1}, "background": {"type": "boolean", "default": False}, "covers": {"type": "array", "items": {"type": "string"}}, "phase": {"type": "string", "enum": ["targeted", "final"], "default": "targeted"}}, ["command"])},
        {"name": "validation_wait", "description": "Wait inside Tide for a background validation.", "inputSchema": _schema({"validation_id": {"type": "string"}, "wait_seconds": {"type": "integer", "minimum": 1, "maximum": 60, "default": 20}}, ["validation_id"])},
        {"name": "validation_log", "description": "Read a saved validation log by log_id or validation_id.", "inputSchema": _schema({"log_id": {"type": "string"}}, ["log_id"])},
        {"name": "convergence", "description": "Record investigation progress or apply the user's continue/stop decision.", "inputSchema": _schema({"summary": {"type": "string"}, "new_evidence": {"type": "boolean", "default": False}, "root_cause_known": {"type": "boolean"}, "next_step": {"type": "string"}, "decision": {"type": "string", "enum": ["continue_one_cycle", "stop_and_report"]}})},
        {"name": "review_packet", "description": "Create or reuse a validated review packet and return the selected reviewer.", "inputSchema": _schema({"full": {"type": "boolean", "default": False}, "full_reason": {"type": "string"}})},
        {"name": "review_get", "description": "Read a review packet and its one-time submission token.", "inputSchema": _schema({"review_id": {"type": "string"}}, ["review_id"])},
        {"name": "review_submit", "description": "Submit the independent reviewer verdict.", "inputSchema": _schema({"review_id": {"type": "string"}, "submission_token": {"type": "string"}, "approved": {"type": "boolean"}, "findings": {"type": "array", "items": _finding_schema()}}, ["review_id", "submission_token", "approved", "findings"])},
        {"name": "operational_verify", "description": "Record rebuild, health, worker, queue, or smoke checks without reopening approved code.", "inputSchema": _schema({"name": {"type": "string"}, "passed": {"type": "boolean"}, "details": {"type": "string"}}, ["name", "passed"])},
        {"name": "authorize", "description": "Record explicit authorization for a genuine pending user decision.", "inputSchema": _schema({"gates": {"type": "array", "items": {"type": "string"}}, "all": {"type": "boolean", "default": False}})},
        {"name": "check", "description": "Evaluate the single deterministic quality and closure state.", "inputSchema": _schema()},
        {"name": "commit_check", "description": "Required gate before git commit. Verifies approval, evidence, and exact staging.", "inputSchema": _schema()},
    ]


def _tool_schema(name: str) -> dict[str, Any]:
    for tool in tools():
        if tool["name"] == name:
            return tool["inputSchema"]
    compatibility = {
        "validation_status": _schema({"validation_id": {"type": "string"}}, ["validation_id"]),
        "handoff": _schema(),
        "status": _schema(),
        "external_acknowledge": _schema({"files": {"type": "array", "items": {"type": "string"}}, "reason": {"type": "string"}}, ["files", "reason"]),
        "abandon": _schema({"reason": {"type": "string"}}, ["reason"]),
        "model_policy": _schema({"phase": {"type": "string"}, "strategy": {"type": "string"}, "review_mode": {"type": "string"}, "failed_attempts": {"type": "integer"}, "root_cause_known": {"type": "boolean"}}),
    }
    if name in compatibility:
        return compatibility[name]
    raise TideError(f"unknown tool: {name}")


def _validate_arguments(name: str, arguments: dict[str, Any]) -> None:
    schema = _tool_schema(name)
    unknown = sorted(set(arguments) - set(schema.get("properties", {})))
    if unknown:
        raise TideError(f"unknown arguments for {name}: {', '.join(unknown)}")
    missing = [key for key in schema.get("required", []) if key not in arguments]
    if missing:
        raise TideError(f"missing arguments for {name}: {', '.join(missing)}")


def _attach_policy(value: Any, *, phase: str | None = None, review_mode: str | None = None) -> Any:
    if not isinstance(value, dict):
        return value
    return {
        **value,
        "model_policy": model_policy(project_root(), phase=phase, review_mode=review_mode),
    }


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    _validate_arguments(name, arguments)
    root = project_root()
    if name == "resume":
        return _attach_policy(resume(root))
    if name == "prepare":
        return _attach_policy(prepare(root, str(arguments["task"]), list(arguments.get("files") or []), list(arguments.get("required_validations") or [])), phase="planning")
    if name == "revise":
        return _attach_policy(revise(root, task=str(arguments["task"]) if arguments.get("task") is not None else None, add_files=list(arguments.get("add_files") or []), remove_files=list(arguments.get("remove_files") or []), add_required_validations=list(arguments.get("add_required_validations") or []), remove_required_validations=list(arguments.get("remove_required_validations") or [])), phase="implementation")
    if name == "split":
        return _attach_policy(split(root, task=str(arguments["task"]), files=list(arguments["files"])), phase="implementation")
    if name == "reopen":
        return _attach_policy(reopen(root, reason=str(arguments["reason"]), code_change_required=bool(arguments.get("code_change_required", False))), phase="correction")
    if name == "validate":
        command = list(arguments["command"])
        timeout = int(arguments.get("timeout", 300))
        covers = list(arguments.get("covers") or [])
        phase = str(arguments.get("phase") or "targeted")
        if bool(arguments.get("background", False)):
            return start_validation(root, command, timeout, covers=covers, phase=phase)
        return record_validation(root, command, timeout, covers=covers, phase=phase)
    if name == "validation_wait":
        return validation_wait(root, str(arguments["validation_id"]), int(arguments.get("wait_seconds", 20)))
    if name == "validation_log":
        return validation_log(root, str(arguments["log_id"]))
    if name == "convergence":
        return _attach_policy(convergence(root, summary=str(arguments.get("summary") or "") or None, new_evidence=bool(arguments.get("new_evidence", False)), root_cause_known=arguments.get("root_cause_known"), next_step=str(arguments.get("next_step") or "") or None, decision=str(arguments.get("decision") or "") or None), phase="investigation")
    if name == "review_packet":
        value = create_review_packet(root, full=bool(arguments.get("full", False)), full_reason=str(arguments.get("full_reason") or "") or None)
        return _attach_policy(value, phase="review", review_mode=str(value.get("review_mode") or "incremental"))
    if name == "review_get":
        return get_review_packet(root, str(arguments["review_id"]))
    if name == "review_submit":
        try:
            return submit_review(root, review_id=str(arguments["review_id"]), submission_token=str(arguments["submission_token"]), approved=bool(arguments["approved"]), findings=list(arguments.get("findings") or []))
        except TideError as exc:
            if "already has a submitted verdict" not in str(exc):
                raise
            packet = read_review_packet(root, str(arguments["review_id"]))
            submission = packet.get("submission")
            if not isinstance(submission, dict):
                raise
            return {**submission, "verdict_submitted": True, "idempotent": True}
    if name == "operational_verify":
        return operational_verify(root, name=str(arguments["name"]), passed=bool(arguments["passed"]), details=str(arguments.get("details") or ""))
    if name == "authorize":
        return authorize(root, list(arguments.get("gates") or []), all_gates=bool(arguments.get("all", False)))
    if name == "check" or name == "status":
        return _attach_policy(check(root))
    if name == "commit_check":
        return commit_check(root)
    if name == "validation_status":
        return validation_status(root, str(arguments["validation_id"]))
    if name == "handoff":
        return handoff(root)
    if name == "external_acknowledge":
        return external_acknowledge(root, list(arguments["files"]), reason=str(arguments["reason"]))
    if name == "abandon":
        return abandon(root, reason=str(arguments["reason"]))
    if name == "model_policy":
        return model_policy(root, phase=str(arguments.get("phase") or "") or None, strategy=str(arguments.get("strategy") or "") or None, review_mode=str(arguments.get("review_mode") or "") or None, failed_attempts=int(arguments["failed_attempts"]) if arguments.get("failed_attempts") is not None else None, root_cause_known=arguments.get("root_cause_known"))
    raise TideError(f"unknown tool: {name}")


def _tool_summary(name: str, value: Any) -> str:
    if not isinstance(value, dict):
        return f"{name}: completed"
    if name in {"resume", "prepare", "revise", "split", "reopen", "check", "status", "convergence"}:
        return f"{name}: lifecycle={value.get('lifecycle')}; ready={bool(value.get('ready'))}; blocker={value.get('primary_blocker') or 'none'}; next={value.get('next_action')}"
    if name == "validate":
        if value.get("reused"):
            return "validate: reused current final evidence"
        if value.get("status") in {"starting", "running"}:
            return f"validate: running as {value.get('validation_id')}"
        return f"validate: {'passed' if value.get('passed') else 'failed'}; log={value.get('log_id', 'pending')}"
    if name == "validation_wait":
        passed = value.get("passed")
        return f"validation_wait: {value.get('status')}; passed={'pending' if passed is None else str(bool(passed)).lower()}; log={value.get('log_id', 'pending')}"
    if name == "review_packet":
        return f"review_packet: {value.get('review_id')}; reviewer={value.get('reviewer_agent')}; files={len(value.get('files') or [])}"
    if name == "review_submit":
        return f"review_submit: {'approved' if value.get('approved') else 'blocked'}; blocking={len(value.get('blocking_findings') or [])}; submitted=true"
    if name == "commit_check":
        return f"commit_check: {'allowed' if value.get('allowed') else 'blocked'}; blocker={(value.get('blockers') or ['none'])[0]}; next={value.get('next_action')}"
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
        respond(request_id, result={"protocolVersion": "2025-03-26", "capabilities": {"tools": {}, "resources": {}}, "serverInfo": {"name": "tide", "version": __version__}, "instructions": INSTRUCTIONS})
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
            packet = get_review_packet(project_root(), parsed.path.strip("/"))
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
