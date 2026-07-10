from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .context import query_context
from .core import check, prepare, preparation_report, record_validation
from .locks import load_locks
from .project import TideError, project_root


INSTRUCTIONS = """Tide is the mandatory quality protocol for code changes.
Load the global tide skill. Call tide_prepare before editing and tide_check before reporting completion.
Use one writer. Use the tide reviewer only when Tide requires review. Treat Module Locks and hardgates as mandatory.
Never commit or push without explicit supervisor approval. Communicate in short, direct, caveman-style messages."""


def tools() -> list[dict[str, Any]]:
    return [
        {"name": "tide_prepare", "description": "Prepare a code change and return boundary, locks, hardgates, validation and review requirements.", "inputSchema": {"type": "object", "properties": {"task": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}}, "required": ["task"]}},
        {"name": "tide_context", "description": "Find relevant live-code context using code-review-graph when supported, otherwise direct search.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
        {"name": "tide_check", "description": "Run the deterministic final quality gate for the current change.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "tide_validate", "description": "Run and record an exact validation command.", "inputSchema": {"type": "object", "properties": {"command": {"type": "array", "items": {"type": "string"}}, "timeout": {"type": "integer", "minimum": 1}}, "required": ["command"]}},
        {"name": "tide_lock_list", "description": "List Module Locks in the current project.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "tide_status", "description": "Show the current Tide preparation and policy.", "inputSchema": {"type": "object", "properties": {}}},
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    root = project_root()
    if name == "tide_prepare":
        return prepare(root, str(arguments["task"]), list(arguments.get("files") or []))
    if name == "tide_context":
        return query_context(root, str(arguments["query"]))
    if name == "tide_check":
        return check(root)
    if name == "tide_validate":
        return record_validation(root, list(arguments["command"]), int(arguments.get("timeout", 300)))
    if name == "tide_lock_list":
        return [{"name": lock.name, "file": str(lock.file.relative_to(root)), "paths": list(lock.paths), "criticality": lock.criticality, "review_required": lock.review_required} for lock in load_locks(root)]
    if name == "tide_status":
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
        respond(request_id, result={"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "serverInfo": {"name": "tide", "version": "0.6.0a1"}, "instructions": INSTRUCTIONS})
    elif method == "tools/list":
        respond(request_id, result={"tools": tools()})
    elif method == "tools/call":
        params = request.get("params") or {}
        try:
            value = call_tool(str(params.get("name")), dict(params.get("arguments") or {}))
            respond(request_id, result={"content": [{"type": "text", "text": json.dumps(value, indent=2, ensure_ascii=False)}], "structuredContent": value, "isError": False})
        except Exception as exc:
            respond(request_id, result={"content": [{"type": "text", "text": str(exc)}], "isError": True})
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
