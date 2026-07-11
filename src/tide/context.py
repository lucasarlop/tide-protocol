from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


MAX_RESULTS = 30
BROAD_TERMS = {
    "architecture",
    "arquitetura",
    "pipeline",
    "flow",
    "fluxo",
    "module",
    "módulo",
    "system",
    "sistema",
}


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
    hits = _direct_search(root, query)
    words = {word.strip(".,:;()[]{}").lower() for word in query.split()}
    broad = bool(words & BROAD_TERMS)
    quality = "good" if len(hits) >= 3 else "insufficient"
    response: dict[str, Any] = {
        "query": query,
        "truth": "current code + git status + current diff + real validations",
        "graph": status,
        "direct_search": hits,
        "context_quality": quality,
    }
    if status["available"]:
        if not status["index_exists"]:
            response["recommended_sequence"] = [
                "build_or_update_graph_tool",
                "get_architecture_overview_tool" if broad else "semantic_search_nodes_tool",
                "get_minimal_context_tool",
            ]
            response["instruction"] = (
                "Build the graph first. Use structural results, then confirm against current code."
            )
        elif broad or quality == "insufficient":
            response["recommended_sequence"] = [
                "get_architecture_overview_tool",
                "semantic_search_nodes_tool",
                "get_minimal_context_tool",
            ]
            response["instruction"] = (
                "The first context is broad or weak. Use architecture overview and semantic search "
                "before starting a wide manual exploration. Confirm findings against current code."
            )
        else:
            response["recommended_sequence"] = [
                "get_minimal_context_tool",
                "query_graph_tool",
                "get_impact_radius_tool",
            ]
            response["instruction"] = (
                "Use the code-review-graph MCP for structural context, then confirm findings "
                "against current code."
            )
    else:
        response["recommended_sequence"] = ["direct_search", "read_current_code"]
        response["instruction"] = (
            "code-review-graph is unavailable. Use direct-search hits and read current code."
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
