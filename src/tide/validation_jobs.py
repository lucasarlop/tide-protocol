from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from .project import TideError, read_json, runtime_dir, write_json


def _safe_id(value: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    if not value or any(char not in allowed for char in value):
        raise TideError(f"invalid validation id: {value}")
    return value


def _jobs_dir(root: Path) -> Path:
    directory = runtime_dir(root) / "validation-jobs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _job_path(root: Path, validation_id: str) -> Path:
    return _jobs_dir(root) / f"{_safe_id(validation_id)}.json"


def save_job(root: Path, job: dict[str, Any]) -> None:
    validation_id = str(job.get("validation_id") or "")
    write_json(_job_path(root, validation_id), job)


def read_job(root: Path, validation_id: str) -> dict[str, Any]:
    value = read_json(_job_path(root, validation_id), None)
    if not isinstance(value, dict):
        raise TideError(f"validation job not found: {validation_id}")
    return value


def start_job(
    root: Path,
    *,
    command: list[str],
    timeout: int,
    files: list[str],
    diff_fingerprint: str,
    revision: int,
    created_at: str,
) -> dict[str, Any]:
    validation_id = f"validation-job-{uuid.uuid4().hex[:16]}"
    job: dict[str, Any] = {
        "validation_id": validation_id,
        "status": "starting",
        "command": list(command),
        "timeout": int(timeout),
        "files": list(files),
        "diff_fingerprint": diff_fingerprint,
        "revision": int(revision),
        "created_at": created_at,
        "recorded": False,
    }
    save_job(root, job)
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tide.validation_worker",
                "--root",
                str(root),
                "--validation-id",
                validation_id,
            ],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError as exc:
        job.update(
            {
                "status": "completed",
                "result": {
                    "command": list(command),
                    "exit_code": 127,
                    "passed": False,
                    "timed_out": False,
                    "duration_seconds": 0.0,
                    "stdout": "",
                    "stderr": str(exc),
                },
            }
        )
        save_job(root, job)
        return compact_job(job)

    latest = read_job(root, validation_id)
    if latest.get("status") == "completed":
        return compact_job(latest)
    latest.update({"status": "running", "pid": process.pid})
    save_job(root, latest)
    return compact_job(latest)


def refresh_job(root: Path, validation_id: str) -> dict[str, Any]:
    job = read_job(root, validation_id)
    if job.get("status") in {"starting", "running"}:
        pid = int(job.get("pid") or 0)
        if pid and not _pid_alive(pid):
            job.update(
                {
                    "status": "completed",
                    "result": {
                        "command": list(job.get("command") or []),
                        "exit_code": 125,
                        "passed": False,
                        "timed_out": False,
                        "duration_seconds": None,
                        "stdout": "",
                        "stderr": "validation worker exited without recording a result",
                    },
                }
            )
            save_job(root, job)
    return job


def compact_job(job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result") if isinstance(job.get("result"), dict) else None
    value: dict[str, Any] = {
        "validation_id": job.get("validation_id"),
        "status": job.get("status"),
        "command": list(job.get("command") or []),
        "created_at": job.get("created_at"),
        "completed_at": job.get("completed_at"),
        "recorded": bool(job.get("recorded")),
    }
    if result is not None:
        value.update(
            {
                "exit_code": result.get("exit_code"),
                "passed": bool(result.get("passed")),
                "timed_out": bool(result.get("timed_out")),
                "duration_seconds": result.get("duration_seconds"),
            }
        )
    if isinstance(job.get("evidence"), dict):
        value["evidence"] = job["evidence"]
    return value


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
