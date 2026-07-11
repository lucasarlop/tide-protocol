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
    prepare,
    preparation_report,
    record_validation,
    reopen,
    revise,
    start_validation,
    submit_review,
    validation_log,
    validation_status,
)
from .locks import load_locks, render_draft
from .project import TideError, project_root


INSTRUCTIONS = """Tide keeps code changes safe and convergent.
Call prepare before editing and check before reporting completion.
Tide selects fast mode for ordinary changes and strict mode for sensitive hardgates or Module Locks.
During implementation run targeted validations only for the files affected by the latest delta. Declare coverage with covers.
Run final validations once near closure. Reuse current evidence for unaffected files.
Create review_packet only after changed files have current passing validation coverage. Reviews after the first are incremental by default.
Review findings must be classified as blocking, follow_up, or info. Only blocking findings stay in the current task.
Do not implement follow-up improvements automatically. Report them for a separate task.
Approved review locks closure: run only final validation and check. Use reopen only for a new blocking defect, then obtain closure_reopen authorization.
When split_required is true, split the task or obtain explicit extended_investigation authorization. Do not continue expanding scope silently.
Use background validation for long commands and poll validation_status.
Do not absorb unrelated files into the boundary; use external_acknowledge for stable client-generated changes.
A truncated review packet cannot be approved. Never commit or push without explicit supervisor approval."""


def _schema(
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "type": "object",
        "properties": properties or {},
        "additionalProperties": False,
    }
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
                    "severity": {
                        "type": "string",
                        "enum": ["blocking", "follow_up", "info"],
                    },
                    "message": {"type": "string"},
                },
                "required": ["severity", "message"],
                "additionalProperties": False,
            },
        ]
    }


def tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "prepare",
            "description": "Prepare a bounded change. Tide automatically selects fast or strict mode.",
            "inputSchema": _schema(
                {
                    "task": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                    "required_validations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Exact commands that must pass before closure.",
                    },
                },
                ["task"],
            ),
        },
        {
            "name": "revise",
            "description": "Revise task, boundary, or validation plan. Evidence for unaffected files is retained.",
            "inputSchema": _schema(
                {
                    "task": {"type": "string"},
                    "add_files": {"type": "array", "items": {"type": "string"}},
                    "remove_files": {"type": "array", "items": {"type": "string"}},
                    "add_required_validations": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "remove_required_validations": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                }
            ),
        },
        {
            "name": "reopen",
            "description": "Reopen an approved closure only for a concrete new blocking defect. Requires closure_reopen authorization before editing.",
            "inputSchema": _schema({"reason": {"type": "string"}}, ["reason"]),
        },
        {
            "name": "external_acknowledge",
            "description": "Acknowledge stable changed files external to the task without adding them to its diff or boundary.",
            "inputSchema": _schema(
                {
                    "files": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"},
                },
                ["files", "reason"],
            ),
        },
        {
            "name": "authorize",
            "description": "Record explicit supervisor authorization for pending hardgates.",
            "inputSchema": _schema(
                {
                    "gates": {"type": "array", "items": {"type": "string"}},
                    "all": {"type": "boolean", "default": False},
                }
            ),
        },
        {
            "name": "context",
            "description": "Return direct live-code context and graph guidance when relevant.",
            "inputSchema": _schema({"query": {"type": "string"}}, ["query"]),
        },
        {
            "name": "check",
            "description": "Run the deterministic closure gate with scoped validation reuse and workflow budget checks.",
            "inputSchema": _schema(),
        },
        {
            "name": "validate",
            "description": "Run a targeted or final validation. covers declares which changed files this evidence validates.",
            "inputSchema": _schema(
                {
                    "command": {"type": "array", "items": {"type": "string"}},
                    "timeout": {"type": "integer", "minimum": 1},
                    "background": {"type": "boolean", "default": False},
                    "covers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task file paths or glob patterns covered by this command. Defaults to all changed task files.",
                    },
                    "phase": {
                        "type": "string",
                        "enum": ["targeted", "final"],
                        "default": "targeted",
                    },
                },
                ["command"],
            ),
        },
        {
            "name": "validation_status",
            "description": "Poll a background validation and record its scoped evidence when complete.",
            "inputSchema": _schema(
                {"validation_id": {"type": "string"}},
                ["validation_id"],
            ),
        },
        {
            "name": "validation_log",
            "description": "Read the full log only when compact evidence is insufficient.",
            "inputSchema": _schema({"log_id": {"type": "string"}}, ["log_id"]),
        },
        {
            "name": "review_packet",
            "description": "Create a validated review packet. Incremental by default after the first review.",
            "inputSchema": _schema(
                {
                    "full": {
                        "type": "boolean",
                        "default": False,
                        "description": "Force a full review only when central architecture or invariants changed.",
                    }
                }
            ),
        },
        {
            "name": "review_get",
            "description": "Read the detailed review packet and its one-time submission token. Intended for tide-reviewer.",
            "inputSchema": _schema(
                {"review_id": {"type": "string"}},
                ["review_id"],
            ),
        },
        {
            "name": "review_submit",
            "description": "Submit the reviewer verdict directly with structured severities. Follow-ups do not block closure.",
            "inputSchema": _schema(
                {
                    "review_id": {"type": "string"},
                    "submission_token": {"type": "string"},
                    "approved": {"type": "boolean"},
                    "findings": {"type": "array", "items": _finding_schema()},
                },
                ["review_id", "submission_token", "approved"],
            ),
        },
        {
            "name": "lock_list",
            "description": "List Module Locks in the current project.",
            "inputSchema": _schema(),
        },
        {
            "name": "lock_template",
            "description": "Generate a short Module Lock draft without writing it.",
            "inputSchema": _schema(
                {
                    "scope": {"type": "string"},
                    "name": {"type": "string"},
                    "criticality": {"type": "string", "default": "production"},
                },
                ["scope", "name"],
            ),
        },
        {
            "name": "status",
            "description": "Show mode, workflow budget, evidence, closure state, and pending hardgates.",
            "inputSchema": _schema(),
        },
    ]


def _tool_schema(name: str) -> dict[str, Any]:
    for tool in tools():
        if tool["name"] == name:
            return tool["inputSchema"]
    raise TideError(f"unknown tool: {name}")


def _validate_arguments(name: str, arguments: dict[str, Any]) -> None:
    schema = _tool_schema(name)
    allowed = set(schema.get("properties", {}))
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise TideError(f"unknown arguments for {name}: {', '.join(unknown)}")
    missing = [key for key in schema.get("required", []) if key not in arguments]
    if missing:
        raise TideError(f"missing arguments for {name}: {', '.join(missing)}")


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    _validate_arguments(name, arguments)
    root = project_root()
    if name == "prepare":
        return prepare(
            root,
            str(arguments["task"]),
            list(arguments.get("files") or []),
            list(arguments.get("required_validations") or []),
        )
    if name == "revise":
        return revise(
            root,
            task=str(arguments["task"]) if arguments.get("task") is not None else None,
            add_files=list(arguments.get("add_files") or []),
            remove_files=list(arguments.get("remove_files") or []),
            add_required_validations=list(arguments.get("add_required_validations") or []),
            remove_required_validations=list(arguments.get("remove_required_validations") or []),
        )
    if name == "reopen":
        return reopen(root, reason=str(arguments["reason"]))
    if name == "external_acknowledge":
        return external_acknowledge(
            root,
            list(arguments["files"]),
            reason=str(arguments["reason"]),
        )
    if name == "authorize":
        return authorize(
            root,
            list(arguments.get("gates") or []),
            all_gates=bool(arguments.get("all", False)),
        )
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
            return start_validation(
                root,
                command,
                timeout,
                covers=covers,
                phase=phase,
            )
        return record_validation(
            root,
            command,
            timeout,
            covers=covers,
            phase=phase,
        )
    if name == "validation_status":
        return validation_status(root, str(arguments["validation_id"]))
    if name == "validation_log":
        return validation_log(root, str(arguments["log_id"]))
    if name == "review_packet":
        return create_review_packet(root, full=bool(arguments.get("full", False)))
    if name == "review_get":
        return get_review_packet(root, str(arguments["review_id"]))
    if name == "review_submit":
        return submit_review(
            root,
            review_id=str(arguments["review_id"]),
            submission_token=str(arguments["submission_token"]),
            approved=bool(arguments["approved"]),
            findings=list(arguments.get("findings") or []),
        )
    if name == "lock_list":
        return [
            {
                "name": lock.name,
                "file": str(lock.file.relative_to(root)),
                "paths": list(lock.paths),
                "criticality": lock.criticality,
                "review_required": lock.review_required,
            }
            for lock in load_locks(root)
        ]
    if name == "lock_template":
        return {
            "content": render_draft(
                name=str(arguments["name"]),
                scope=str(arguments["scope"]),
                criticality=str(arguments.get("criticality", "production")),
            )
        }
    if name == "status":
        return preparation_report(root)
    raise TideError(f"unknown tool: {name}")


def _tool_summary(name: str, value: Any) -> str:
    if not isinstance(value, dict):
        return f"{name}: completed"
    if name in {"prepare", "revise", "reopen", "status"}:
        return (
            f"{name}: mode={value.get('mode')}; "
            f"mutation_allowed={bool(value.get('mutation_allowed'))}; "
            f"split_required={bool(value.get('split_required'))}; "
            f"closure_locked={bool(value.get('closure_locked'))}"
        )
    if name == "external_acknowledge":
        return f"external_acknowledge: {len(value.get('acknowledged') or [])} file(s)"
    if name == "validate":
        if value.get("validation_id") and value.get("status") in {"starting", "running"}:
            return f"validate: running as {value['validation_id']}; phase={value.get('phase')}"
        return (
            f"validate: {'passed' if value.get('passed') else 'failed'}; "
            f"phase={value.get('phase')}; log={value.get('log_id', 'pending')}"
        )
    if name == "validation_status":
        return f"validation_status: {value.get('status')}; passed={bool(value.get('passed'))}"
    if name == "review_packet":
        return (
            f"review_packet: {value.get('review_id')}; mode={value.get('review_mode')}; "
            f"files={len(value.get('files') or [])}; truncated={bool(value.get('diff_truncated'))}"
        )
    if name == "review_submit":
        return (
            f"review_submit: {'approved' if value.get('approved') else 'blocked'}; "
            f"blocking={len(value.get('blocking_findings') or [])}; "
            f"follow_up={len(value.get('follow_up_findings') or [])}"
        )
    if name == "check":
        return (
            f"check: {'ready' if value.get('ready') else 'blocked'}; "
            f"blockers={len(value.get('blockers') or [])}; "
            f"follow_up={len(value.get('follow_up_tasks') or [])}"
        )
    if name == "validation_log":
        return f"validation_log: {value.get('log_id')}"
    return f"{name}: completed"


def respond(request_id: Any, *, result: Any = None, error: str | None = None) -> None:
    if request_id is None:
        return
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error:
        payload["error"] = {"code": -32000, "message": error}
    else:
        payload["result"] = result
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def handle(request: dict[str, Any]) -> None:
    request_id = request.get("id")
    method = request.get("method")
    if method == "initialize":
        respond(
            request_id,
            result={
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "tide", "version": "0.6.0a6"},
                "instructions": INSTRUCTIONS,
            },
        )
        return
    if method == "tools/list":
        respond(request_id, result={"tools": tools()})
        return
    if method == "tools/call":
        params = request.get("params") or {}
        try:
            name = str(params.get("name"))
            value = call_tool(name, dict(params.get("arguments") or {}))
            respond(
                request_id,
                result={
                    "content": [{"type": "text", "text": _tool_summary(name, value)}],
                    "structuredContent": value,
                    "isError": False,
                },
            )
        except Exception as exc:
            respond(
                request_id,
                result={
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
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
            respond(
                request_id,
                result={
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(packet, indent=2, ensure_ascii=False),
                        }
                    ]
                },
            )
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
