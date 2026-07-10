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
    record_review,
    record_validation,
    revise,
    validation_log,
)
from .locks import load_locks, render_draft
from .project import TideError, project_root


INSTRUCTIONS = """Tide is the mandatory quality protocol for code changes.
Load the global Tide skill. Call prepare before editing and check before reporting completion.
Use revise, not a new prepare, when the task or boundary changes. Do not edit while mutation_allowed is false.
Use one writer. Create a review packet only when review is required; pass its review_id to tide-reviewer.
The reviewer reads the packet with review_get. Do not relay full diffs or validation logs through the main agent.
Treat Module Locks and pending hardgates as mandatory. Never commit or push without explicit supervisor approval.
Use code-review-graph MCP tools when available, then confirm against current code.
Do not announce routine steps or maintain visible todos unless requested. Interrupt only for authorization, blockers, or the final checkpoint."""


def tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "prepare",
            "description": "Prepare a code change. Returns boundary, Module Locks, hardgates, validations, and whether mutation is allowed.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["task"],
            },
        },
        {
            "name": "revise",
            "description": "Revise the active task or boundary without resetting the original baseline. Invalidates validation and review evidence.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "add_files": {"type": "array", "items": {"type": "string"}},
                    "remove_files": {"type": "array", "items": {"type": "string"}},
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
            "description": "Run and record a validation command. Returns compact evidence and a log_id; use validation_log only for failure diagnosis.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {"type": "array", "items": {"type": "string"}},
                    "timeout": {"type": "integer", "minimum": 1},
                },
                "required": ["command"],
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
            "description": "Read the detailed review packet by review_id. Intended for tide-reviewer, not the main writer.",
            "inputSchema": {
                "type": "object",
                "properties": {"review_id": {"type": "string"}},
                "required": ["review_id"],
            },
        },
        {
            "name": "record_review",
            "description": "Record the independent review verdict and concise findings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "approved": {"type": "boolean"},
                    "findings": {"type": "array", "items": {"type": "string"}},
                    "review_id": {"type": "string"},
                },
                "required": ["approved"],
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
            "description": "Show the current Tide preparation and policy.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    root = project_root()
    if name == "prepare":
        return prepare(root, str(arguments["task"]), list(arguments.get("files") or []))
    if name == "revise":
        return revise(
            root,
            task=str(arguments["task"]) if arguments.get("task") is not None else None,
            add_files=list(arguments.get("add_files") or []),
            remove_files=list(arguments.get("remove_files") or []),
        )
    if name == "authorize":
        return authorize(root, list(arguments.get("gates") or []), all_gates=bool(arguments.get("all", False)))
    if name == "context":
        return query_context(root, str(arguments["query"]))
    if name == "check":
        return check(root)
    if name == "validate":
        return record_validation(root, list(arguments["command"]), int(arguments.get("timeout", 300)))
    if name == "validation_log":
        return validation_log(root, str(arguments["log_id"]))
    if name == "review_packet":
        return create_review_packet(root)
    if name == "review_get":
        return get_review_packet(root, str(arguments["review_id"]))
    if name == "record_review":
        return record_review(
            root,
            approved=bool(arguments["approved"]),
            findings=list(arguments.get("findings") or []),
            review_id=str(arguments["review_id"]) if arguments.get("review_id") else None,
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
                "serverInfo": {"name": "tide", "version": "0.6.0a3"},
                "instructions": INSTRUCTIONS,
            },
        )
    elif method == "tools/list":
        respond(request_id, result={"tools": tools()})
    elif method == "tools/call":
        params = request.get("params") or {}
        try:
            value = call_tool(str(params.get("name")), dict(params.get("arguments") or {}))
            respond(
                request_id,
                result={
                    "content": [{"type": "text", "text": json.dumps(value, indent=2, ensure_ascii=False)}],
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
            respond(request_id, result={"resources": list_review_resources(project_root())})
        except Exception as exc:
            respond(request_id, error=str(exc))
    elif method == "resources/read":
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
