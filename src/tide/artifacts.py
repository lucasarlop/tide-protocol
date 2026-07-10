from __future__ import annotations

import json
import shlex
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import TideError, read_json, runtime_dir, write_json


TAIL_LINES = 20


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f")


def _safe_id(value: str, *, label: str) -> str:
    if not value or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for char in value):
        raise TideError(f"invalid {label}: {value}")
    return value


def _tail(text: str, limit: int = TAIL_LINES) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-limit:]


def save_validation_log(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    log_id = f"validation-{_timestamp()}-{uuid.uuid4().hex[:8]}"
    directory = runtime_dir(root) / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{log_id}.log"
    command = " ".join(shlex.quote(str(item)) for item in result.get("command", []))
    stdout = str(result.get("stdout") or "")
    stderr = str(result.get("stderr") or "")
    content = (
        f"command: {command}\n"
        f"exit_code: {result.get('exit_code')}\n"
        f"timed_out: {bool(result.get('timed_out'))}\n"
        f"duration_seconds: {result.get('duration_seconds')}\n\n"
        "--- stdout ---\n"
        f"{stdout}\n\n"
        "--- stderr ---\n"
        f"{stderr}\n"
    )
    path.write_text(content, encoding="utf-8")
    return {
        "log_id": log_id,
        "log_path": str(path.relative_to(runtime_dir(root))),
        "stdout_tail": _tail(stdout),
        "stderr_tail": _tail(stderr),
        "stdout_bytes": len(stdout.encode("utf-8", errors="replace")),
        "stderr_bytes": len(stderr.encode("utf-8", errors="replace")),
    }


def read_validation_log(root: Path, log_id: str) -> dict[str, Any]:
    safe = _safe_id(log_id, label="validation log id")
    path = runtime_dir(root) / "logs" / f"{safe}.log"
    if not path.exists():
        raise TideError(f"validation log not found: {log_id}")
    return {
        "log_id": safe,
        "content": path.read_text(encoding="utf-8"),
    }


def save_review_packet(root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    fingerprint = str(packet.get("diff_fingerprint") or "no-diff")
    review_id = f"review-{fingerprint[:12]}-{uuid.uuid4().hex[:8]}"
    directory = runtime_dir(root) / "reviews"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{review_id}.json"
    payload = {**packet, "review_id": review_id}
    write_json(path, payload)
    return {
        "review_id": review_id,
        "resource": f"tide://reviews/{review_id}",
        "files": list(packet.get("files") or []),
        "diff_bytes": int((packet.get("diff") or {}).get("bytes", 0)),
        "diff_truncated": bool((packet.get("diff") or {}).get("truncated", False)),
        "validation_count": len(packet.get("validations") or []),
        "stale_validation_count": int(packet.get("stale_validation_count", 0)),
        "review_focus": list(packet.get("review_focus") or []),
    }


def read_review_packet(root: Path, review_id: str) -> dict[str, Any]:
    safe = _safe_id(review_id, label="review id")
    path = runtime_dir(root) / "reviews" / f"{safe}.json"
    value = read_json(path, None)
    if not isinstance(value, dict):
        raise TideError(f"review packet not found: {review_id}")
    return value


def list_review_resources(root: Path) -> list[dict[str, str]]:
    directory = runtime_dir(root) / "reviews"
    if not directory.exists():
        return []
    resources: list[dict[str, str]] = []
    for path in sorted(directory.glob("review-*.json")):
        resources.append(
            {
                "uri": f"tide://reviews/{path.stem}",
                "name": path.stem,
                "mimeType": "application/json",
            }
        )
    return resources
