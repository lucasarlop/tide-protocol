"""Safe Tide MCP server.

The server exposes Tide context and planning only. It does not execute project commands, commit changes, or mutate the repository. Mutating actions remain in the Tide CLI and OpenCode commands under explicit supervisor control.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

VERSION = "1.0.0"


def find_project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return current


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def project_profile() -> dict[str, Any]:
    root = find_project_root()
    catalogs = [root / "tide.commands.json", root / ".tide.commands.json", root / ".tide/commands.json", root / ".opencode/tide/commands.json"]
    return {
        "root": str(root),
        "git": (root / ".git").exists(),
        "waves_dir": str(root / ".opencode/waves"),
        "waves_exists": (root / ".opencode/waves").exists(),
        "package_json": (root / "package.json").exists(),
        "makefile": any((root / name).exists() for name in ["Makefile", "makefile"]),
        "pyproject": (root / "pyproject.toml").exists(),
        "docker_compose": any((root / name).exists() for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]),
        "command_catalogs": [str(path.relative_to(root)) for path in catalogs if path.exists()],
        "code_review_graph_available": bool(shutil.which("code-review-graph")),
        "code_review_graph_exists": (root / ".code-review-graph").exists(),
    }


def wave_registry() -> list[dict[str, Any]]:
    root = find_project_root()
    return read_json(root / ".opencode/waves/registry.json", {"waves": []}).get("waves", [])


def wave_markdown(wave_id: str) -> str:
    root = find_project_root()
    path = root / ".opencode/waves" / wave_id / "wave.md"
    if not path.exists():
        return f"Wave não encontrada: {wave_id}"
    return path.read_text(encoding="utf-8")


def command_catalog() -> dict[str, Any]:
    root = find_project_root()
    commands: dict[str, Any] = {}
    package = root / "package.json"
    package_data = read_json(package, {})
    for name, script in (package_data.get("scripts") or {}).items():
        commands[f"npm:{name}"] = {
            "description": f"package.json script {name}",
            "command": f"npm run {name}",
            "source": "package.json",
            "safety": "local",
            "requires_ok": False,
            "raw": script,
        }
    for catalog in [root / "tide.commands.json", root / ".tide.commands.json", root / ".tide/commands.json", root / ".opencode/tide/commands.json"]:
        data = read_json(catalog, {})
        for name, spec in (data.get("commands") or {}).items():
            item = dict(spec)
            item["source"] = str(catalog.relative_to(root))
            commands[name] = item
    return commands


def tools() -> list[dict[str, Any]]:
    return [
        {"name": "tide_project_profile", "description": "Describe the current project and Tide state.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "tide_wave_list", "description": "List Tide Waves from the local registry.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "tide_wave_show", "description": "Show a Tide Wave markdown file.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
        {"name": "tide_commands_list", "description": "List discovered and cataloged project commands without running them.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "tide_command_plan", "description": "Return the supervised Tide CLI command for a cataloged command.", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "args": {"type": "object"}}, "required": ["name"]}},
        {"name": "tide_context_status", "description": "Report code-review-graph availability.", "inputSchema": {"type": "object", "properties": {}}},
    ]


def call_tool(name: str, args: dict[str, Any]) -> tuple[bool, str]:
    if name == "tide_project_profile":
        return False, json.dumps(project_profile(), indent=2, ensure_ascii=False)
    if name == "tide_wave_list":
        return False, json.dumps(wave_registry(), indent=2, ensure_ascii=False)
    if name == "tide_wave_show":
        return False, wave_markdown(args["id"])
    if name == "tide_commands_list":
        return False, json.dumps(command_catalog(), indent=2, ensure_ascii=False)
    if name == "tide_command_plan":
        arg_text = " ".join(f"--arg {key}={value}" for key, value in (args.get("args") or {}).items())
        return False, f"Após OK do supervisor quando necessário:\n\ntide project run {args['name']} {arg_text}".strip()
    if name == "tide_context_status":
        profile = project_profile()
        return False, json.dumps({
            "code_review_graph_available": profile["code_review_graph_available"],
            "code_review_graph_exists": profile["code_review_graph_exists"],
            "truth": "código atual + git status + diff + validações reais",
        }, indent=2, ensure_ascii=False)
    return True, f"tool desconhecida: {name}"


def respond(request_id: Any, result: Any = None, error: str | None = None) -> None:
    if request_id is None:
        return
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is None:
        payload["result"] = result
    else:
        payload["error"] = {"code": -32000, "message": error}
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def prompt_messages() -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": "Defina a menor Wave segura com intenção, fronteira, durabilidade, validação e checkpoint.",
            },
        }
    ]


def handle(request: dict[str, Any]) -> None:
    request_id = request.get("id")
    method = request.get("method")
    if method == "initialize":
        respond(request_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}, "resources": {}, "prompts": {}}, "serverInfo": {"name": "tide", "version": VERSION}})
    elif method == "tools/list":
        respond(request_id, {"tools": tools()})
    elif method == "tools/call":
        params = request.get("params") or {}
        is_error, text = call_tool(params.get("name"), params.get("arguments") or {})
        respond(request_id, {"content": [{"type": "text", "text": text}], "isError": is_error})
    elif method == "resources/list":
        respond(request_id, {"resources": [{"uri": "tide://project/profile", "name": "Tide project profile", "mimeType": "application/json"}]})
    elif method == "resources/read":
        respond(request_id, {"contents": [{"uri": "tide://project/profile", "mimeType": "application/json", "text": json.dumps(project_profile(), indent=2, ensure_ascii=False)}]})
    elif method == "prompts/list":
        respond(request_id, {"prompts": [{"name": "tide-wave", "description": "Define the smallest safe Wave"}]})
    elif method == "prompts/get":
        respond(request_id, {"description": "Define the smallest safe Wave", "messages": prompt_messages()})
    elif method == "ping":
        respond(request_id, {})
    else:
        respond(request_id, error=f"método desconhecido: {method}")


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            handle(json.loads(line))
        except Exception as exc:
            respond(None, error=str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
