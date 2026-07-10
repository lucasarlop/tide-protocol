from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


MAX_RESULTS = 30


def graph_status(root: Path) -> dict[str, Any]:
    executable = shutil.which("code-review-graph")
    index_exists = (root / ".code-review-graph").exists()
    query_supported = False
    if executable:
        help_result = subprocess.run([executable, "--help"], text=True, capture_output=True, timeout=10)
        query_supported = "query" in (help_result.stdout + help_result.stderr).lower()
    return {
        "available": bool(executable),
        "index_exists": index_exists,
        "query_supported": query_supported,
        "executable": executable,
    }


def query_context(root: Path, query: str) -> dict[str, Any]:
    status = graph_status(root)
    if status["available"] and status["query_supported"]:
        result = subprocess.run(
            [status["executable"], "query", "--repo", str(root), "--json", query],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0:
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError:
                payload = result.stdout.strip()
            return {"source": "code-review-graph", "query": query, "result": payload, "status": status}

    return {
        "source": "direct-search",
        "query": query,
        "result": _direct_search(root, query),
        "status": status,
        "warning": "code-review-graph query unavailable; verify all findings against current code",
    }


def _direct_search(root: Path, query: str) -> list[dict[str, Any]]:
    command = shutil.which("rg")
    if not command:
        return []
    result = subprocess.run(
        [command, "--line-number", "--smart-case", "--glob", "!/.git", "--", query, "."],
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
