from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any


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
            "stdout": _text(exc.stdout or ""),
            "stderr": _text(exc.stderr or ""),
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
            "stderr": str(exc),
        }

    duration = round(time.monotonic() - started, 3)
    return {
        "command": command,
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "timed_out": False,
        "duration_seconds": duration,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _text(value: str | bytes) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else value
