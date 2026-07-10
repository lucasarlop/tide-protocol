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
    get_review_packet,
    prepare,
    preparation_report,
    record_validation,
    revise,
    start_validation,
    submit_review,
    validation_log,
    validation_status,
)
from .locks import load_locks, render_draft
from .project import TideError, project_root


INSTRUCTIONS = """Tide is the mandatory quality protocol for code changes.
Load the global Tide skill. Call prepare before editing and check before reporting completion.
Declare the validations that must be current for the final diff. Use revise, not a new prepare, when the task, boundary, or validation plan changes.
Do not edit while mutation_allowed is false. Use one writer.
Use validate with background=true for commands likely to outlive the MCP request, then poll validation_status.
Create a review packet only when review is required; pass its review_id to tide-reviewer.
The reviewer reads the packet with review_get and submits the verdict directly with review_submit using the packet token.
The writer must not relay or rewrite reviewer findings.
Treat Module Locks and pending hardgates as mandatory. Never commit or push without explicit supervisor approval.
Use code-review-graph MCP tools before implementation when available, then confirm against current code.
Do not announce routine steps or maintain visible todos unless requested. Interrupt only for authorization, blockers, or the final checkpoint."""


def tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "prepare",
            "description": "Prepare a code change with its boundary and explicit validation plan.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                    "required_validations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Exact commands that must pass for the final diff.",
                    },
                },
                "required": ["task"],
            },
        },
        {
            "name": "revise",
            "description": "Revise the active task, boundary, or validation plan without resetting the original baseline. Invalidates validation and review evidence.",
            "inputSchema": {
                "type": "object",
                "properties": {
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
                },
            },
        },
        {
            "name": "authorize",
            "description": "Record explicit supervisor authorization for pending hardgates. This is a sensitive action.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "gates": {"type": "array", "items": {"type": "string"}},
                    "all": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": "context",
            "description": "Return direct live-code search and the next code-review-graph tools to use based on context quality.",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        {
            "name": "check",
            "description": "Run the deterministic final quality gate for the current change.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "validate",
            "description": "Run and record a validation command. Set background=true for long commands; poll validation_status with the returned validation_id.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {"type": "array", "items": {"type": "string"}},
                    "timeout": {"type": "integer", "minimum": 1},
                    "background": {"type": "boolean", "default": False},
                },
                "required": ["command"],
            },
        },
        {
            "name": "validation_status",
            "description": "Poll a background validation. Completed jobs are recorded against the diff fingerprint captured at start.",
            "inputSchema": {
                "type": "object",
                "properties": {"validation_id": {"type": "string"}},
                "required": ["validation_id"],
            },
        },
        {
            "name": "validation_log",
            "description": "Read a full validation log by log_id. Use only when compact evidence is insufficient.",
            "inputSchema": {
                "type": "object",
                "properties": {"log_id": {"type": "string"}},
                "required": ["log_id"],
            },
        },
        {
            "name": "review_packet",
            "description": "Create and store a review packet. Returns only review_id, resource URI, counts, and focus.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "review_get",
            "description": "Read the detailed review packet, including the one-time submission token. Intended for tide-reviewer, not the writer.",
            "inputSchema": {
                "type": "object",
                "properties": {"review_id": {"type": "string"}},
                "required": ["review_id"],
            },
        },
        {
            "name": "review_submit",
            "description": "Submit the independent reviewer verdict directly. Requires the packet's one-time submission token.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "review_id": {"type": "string"},
                    "submission_token": {"type": "string"},
                    "approved": {"type": "boolean"},
                    "findings": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["review_id", "submission_token", "approved"],
            },
        },
        {
            "name": "lock_list",
            "description": "List Module Locks in the current project.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "lock_template",
            "description": "Generate a short Module Lock draft without writing it to disk.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string"},
                    "name": {"type": "string"},
                    "criticality": {"type": "string", "default": "production"},
                },
                "required": ["scope", "name"],
            },
        },
        {
            "name": "status",
            "description": "Show the current Tide preparation, validation plan, and policy.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
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
        if bool(arguments.get("background", False)):
            return start_validation(root, command, timeout)
        return record_validation(root, command, timeout)
    if name == "validation_status":
        return validation_status(root, str(arguments["validation_id"]))
    if name == "validation_log":
        return validation_log(root, str(arguments["log_id"]))
    if name == "review_packet":
        return create_review_packet(root)
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
                "serverInfo": {"name": "tide", "version": "0.6.0a4"},
                "instructions": INSTRUCTIONS,
            },
        )
    elif method == "tools/list":
        respond(request_id, result={"tools": tools()})
    elif method == "tools/call":
        params = request.get("params") or {}
        try:
            value = call_tool(
                str(params.get("name")),
                dict(params.get("arguments") or {}),
            )
            respond(
                request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(value, indent=2, ensure_ascii=False),
                        }
                    ],
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
    elif method == "resources/list":
        try:
            respond(
                request_id,
                result={"resources": list_review_resources(project_root())},
            )
        except Exception as exc:
            respond(request_id, error=str(exc))
    elif method == "resources/read":
        try:
            uri = str((request.get("params") or {}).get("uri", ""))
            parsed = urlparse(uri)
            if (
                parsed.scheme != "tide"
                or parsed.netloc != "reviews"
                or not parsed.path.strip("/")
            ):
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
    elif method == "ping":
        respond(request_id, result={})
    else:
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
