from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


MAX_RESULTS = 30


def graph_status(root: Path) -> dict[str, Any]:
    executable = shutil.which("code-review-graph")
    return {
        "available": bool(executable),
        "index_exists": (root / ".code-review-graph").exists(),
        "executable": executable,
        "mcp_command": [executable, "serve"] if executable else None,
    }


def query_context(root: Path, query: str) -> dict[str, Any]:
    status = graph_status(root)
    response: dict[str, Any] = {
        "query": query,
        "truth": "current code + git status + current diff + real validations",
        "graph": status,
        "direct_search": _direct_search(root, query),
    }
    if status["available"]:
        response["preferred_graph_tools"] = [
            "get_minimal_context_tool",
            "semantic_search_nodes_tool",
            "query_graph_tool",
            "get_impact_radius_tool",
        ]
        response["instruction"] = (
            "Use the code-review-graph MCP for structural context, then confirm findings "
            "against current code. Tide does not duplicate the graph implementation."
        )
    else:
        response["instruction"] = (
            "code-review-graph is unavailable. Use the direct-search hits and read current code."
        )
    return response


def _direct_search(root: Path, query: str) -> list[dict[str, Any]]:
    command = shutil.which("rg")
    if not command:
        return []
    result = subprocess.run(
        [command, "--line-number", "--smart-case", "--glob", "!.git/**", "--", query, "."],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=30,
    )
    rows: list[dict[str, Any]] = []
    for line in result.stdout.splitlines()[:MAX_RESULTS]:
        try:
            path, number, text = line.split(":", 2)
        except ValueError:
            continue
        rows.append({"path": path.removeprefix("./"), "line": int(number), "text": text.strip()})
    return rows
