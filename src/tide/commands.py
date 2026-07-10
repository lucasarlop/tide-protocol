from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any


OUTPUT_LIMIT = 12_000


def run_validation(
    root: Path,
    command: list[str],
    timeout: int = 300,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
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
    except OSError as exc:
        duration = round(time.monotonic() - started, 3)
        return {
            "command": command,
            "exit_code": 127,
            "passed": False,
            "timed_out": False,
            "duration_seconds": duration,
            "stdout": "",
            "stderr": _clip(str(exc)),
        }

    duration = round(time.monotonic() - started, 3)
    return {
        "command": command,
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "timed_out": False,
        "duration_seconds": duration,
        "stdout": _clip(result.stdout),
        "stderr": _clip(result.stderr),
    }


def _clip(value: str | bytes) -> str:
    text = value.decode(errors="replace") if isinstance(value, bytes) else value
    if len(text) <= OUTPUT_LIMIT:
        return text
    return text[:OUTPUT_LIMIT] + "\n...[truncated by Tide]"
