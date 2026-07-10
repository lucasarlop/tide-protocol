from __future__ import annotations

import json
import secrets
import shlex
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .project import TideError, read_json, runtime_dir, write_json


TAIL_LINES = 20
TAIL_LINE_CHARS = 400
TAIL_TOTAL_BYTES = 4096


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f")


def _safe_id(value: str, *, label: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    if not value or any(char not in allowed for char in value):
        raise TideError(f"invalid {label}: {value}")
    return value


def _clip_line(line: str) -> str:
    if len(line) <= TAIL_LINE_CHARS:
        return line
    return line[: TAIL_LINE_CHARS - 16] + "...[line clipped]"


def _tail(
    text: str,
    limit: int = TAIL_LINES,
    max_bytes: int = TAIL_TOTAL_BYTES,
) -> list[str]:
    lines = [_clip_line(line) for line in text.splitlines() if line.strip()]
    selected: list[str] = []
    used = 0
    for line in reversed(lines[-limit:]):
        encoded = len(line.encode("utf-8", errors="replace")) + 1
        if selected and used + encoded > max_bytes:
            break
        if not selected and encoded > max_bytes:
            line = line.encode("utf-8", errors="replace")[: max_bytes - 20].decode(
                "utf-8", errors="ignore"
            ) + "...[tail clipped]"
            encoded = len(line.encode("utf-8", errors="replace"))
        selected.append(line)
        used += encoded
    return list(reversed(selected))


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
    try:
        path.chmod(0o600)
    except OSError:
        pass
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


def _review_path(root: Path, review_id: str) -> Path:
    safe = _safe_id(review_id, label="review id")
    return runtime_dir(root) / "reviews" / f"{safe}.json"


def save_review_packet(root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    fingerprint = str(packet.get("diff_fingerprint") or "no-diff")
    review_id = f"review-{fingerprint[:12]}-{uuid.uuid4().hex[:8]}"
    directory = runtime_dir(root) / "reviews"
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        **packet,
        "review_id": review_id,
        "submission_token": secrets.token_urlsafe(32),
        "submission": None,
    }
    write_json(_review_path(root, review_id), payload)
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
    value = read_json(_review_path(root, review_id), None)
    if not isinstance(value, dict):
        raise TideError(f"review packet not found: {review_id}")
    return value


def consume_review_submission(
    root: Path,
    review_id: str,
    submission_token: str,
    submission: dict[str, Any],
) -> dict[str, Any]:
    packet = read_review_packet(root, review_id)
    if packet.get("submission"):
        raise TideError("review packet already has a submitted verdict")
    expected = str(packet.get("submission_token") or "")
    if not expected or not secrets.compare_digest(expected, submission_token):
        raise TideError("invalid review submission token")
    receipt = {
        **submission,
        "receipt_id": f"review-receipt-{uuid.uuid4().hex[:16]}",
    }
    packet["submission"] = receipt
    packet.pop("submission_token", None)
    write_json(_review_path(root, review_id), packet)
    return receipt


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
