from __future__ import annotations

import json
import sys
from typing import Any

from .context import query_context
from .core import (
    authorize,
    check,
    prepare,
    preparation_report,
    record_review,
    record_validation,
    review_packet,
)
from .locks import load_locks, render_draft
from .project import TideError, project_root


INSTRUCTIONS = """Tide is the mandatory quality protocol for code changes.
Load the global Tide skill. Call the Tide prepare tool before editing and Tide check before reporting completion.
Do not edit while mutation_allowed is false. Use one writer. Use tide-reviewer only when Tide requires review.
Treat Module Locks and pending hardgates as mandatory. Never commit or push without explicit supervisor approval.
Use code-review-graph MCP tools when available, then confirm against current code. Communicate in short, direct messages."""


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
            "description": "Return direct live-code search plus guidance for the code-review-graph MCP tools.",
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
            "description": "Run and record an exact validation command. This executes a local process and requires approval by the host.",
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
            "name": "review_packet",
            "description": "Return a compact read-only packet for tide-reviewer: task, diff, locks, validations, and focus.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "record_review",
            "description": "Record the independent review verdict and concise findings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "approved": {"type": "boolean"},
                    "findings": {"type": "array", "items": {"type": "string"}},
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
    if name == "authorize":
        return authorize(root, list(arguments.get("gates") or []), all_gates=bool(arguments.get("all", False)))
    if name == "context":
        return query_context(root, str(arguments["query"]))
    if name == "check":
        return check(root)
    if name == "validate":
        return record_validation(root, list(arguments["command"]), int(arguments.get("timeout", 300)))
    if name == "review_packet":
        return review_packet(root)
    if name == "record_review":
        return record_review(root, approved=bool(arguments["approved"]), findings=list(arguments.get("findings") or []))
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
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "tide", "version": "0.6.0a1"},
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
