from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any


OUTPUT_LIMIT = 12000


def run_validation(root: Path, command: list[str], timeout: int = 300) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        duration = round(time.monotonic() - started, 3)
        return {
            "command": command,
            "exit_code": 124,
            "passed": False,
            "timed_out": True,
            "duration_seconds": duration,
            "stdout": _clip(exc.stdout or ""),
            "stderr": _clip(exc.stderr or ""),
        }
    duration = round(time.monotonic() - started, 3)
    return {
        "command": command,
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "timed_out": timed_out,
        "duration_seconds": duration,
        "stdout": _clip(result.stdout),
        "stderr": _clip(result.stderr),
    }


def _clip(value: str) -> str:
    if len(value) <= OUTPUT_LIMIT:
        return value
    return value[:OUTPUT_LIMIT] + "\n...[truncated by Tide]"
