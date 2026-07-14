from __future__ import annotations

import hashlib
import shlex
from pathlib import Path
from typing import Any, Sequence

from .project import diff_fingerprint, file_fingerprints, is_tracked_in_head, run_git

_SHELLS = {"sh", "bash", "zsh", "dash", "fish"}
_SHELL_FLAGS = {"-c", "-lc", "-ic"}


def canonical_command(command: str | Sequence[Any]) -> tuple[str, ...]:
    if isinstance(command, str):
        return _shell_tokens(command.strip())
    parts = tuple(str(part) for part in command)
    if len(parts) >= 3 and Path(parts[0]).name in _SHELLS and parts[1] in _SHELL_FLAGS:
        return (*_shell_tokens(parts[2]), *parts[3:])
    return parts


def display_command(command: str | Sequence[Any]) -> str:
    if isinstance(command, str):
        return command.strip()
    return " ".join(str(part) for part in command)


def command_matches(required: str, evidence_command: str | Sequence[Any]) -> bool:
    return canonical_command(required) == canonical_command(evidence_command)


def evidence_is_current(root: Path, evidence: dict[str, Any]) -> bool:
    fingerprints = evidence.get("coverage_fingerprints")
    if isinstance(fingerprints, dict):
        paths = sorted(str(path) for path in fingerprints)
        return fingerprints == file_fingerprints(root, paths)
    files = list(evidence.get("files") or [])
    return evidence.get("diff_fingerprint") == diff_fingerprint(root, files)


def current_validations(root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in state.get("validations", [])
        if isinstance(item, dict) and evidence_is_current(root, item)
    ]


def effective_validations(root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return current evidence with older identical failures superseded by later runs."""
    values = current_validations(root, state)
    latest: dict[tuple[tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}
    order: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    for item in values:
        key = (
            canonical_command(item.get("command", [])),
            tuple(sorted(str(path) for path in item.get("files", []))),
        )
        if key not in latest:
            order.append(key)
        latest[key] = item
    return [latest[key] for key in order]


def missing_required_validations(
    required: list[str],
    validations: list[dict[str, Any]],
) -> list[str]:
    passed = [item for item in validations if item.get("passed")]
    return [
        command
        for command in required
        if not any(command_matches(command, item.get("command", [])) for item in passed)
    ]


def required_validation_status(
    required: list[str],
    validations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    passed = [item for item in validations if item.get("passed")]
    result: list[dict[str, Any]] = []
    for command in required:
        match = next(
            (
                display_command(item.get("command", []))
                for item in passed
                if command_matches(command, item.get("command", []))
            ),
            None,
        )
        result.append(
            {
                "required": command,
                "matched": match is not None,
                "matched_command": match,
            }
        )
    return result


def uncovered_files(
    task_files: list[str],
    validations: list[dict[str, Any]],
) -> list[str]:
    covered: set[str] = set()
    for item in validations:
        if item.get("passed"):
            covered.update(str(path) for path in item.get("files", []))
    return sorted(set(task_files) - covered)


def content_fingerprints(root: Path, files: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in sorted(files):
        path = root / name
        if path.is_symlink():
            payload = f"symlink:{path.readlink()}".encode()
        elif path.is_file():
            executable = bool(path.stat().st_mode & 0o111)
            payload = (b"x:" if executable else b"f:") + path.read_bytes()
        elif path.exists():
            payload = b"directory"
        else:
            payload = b"missing"
        result[name] = hashlib.sha256(payload).hexdigest()
    return result


def approval_proof(root: Path, state: dict[str, Any], task_files: list[str]) -> dict[str, Any] | None:
    approved = state.get("approved_snapshot")
    if isinstance(approved, dict):
        expected = approved.get("files")
        if isinstance(expected, dict) and set(expected) == set(task_files):
            if expected == file_fingerprints(root, task_files):
                return {
                    "type": "current_review",
                    "review_id": approved.get("review_id"),
                    "segment_id": (state.get("segments") or {}).get("current_id"),
                }

    current = file_fingerprints(root, task_files) if task_files else {}
    receipts = (state.get("segments") or {}).get("receipts", [])
    for receipt in reversed(receipts):
        if not isinstance(receipt, dict):
            continue
        expected = receipt.get("files")
        if isinstance(expected, dict) and expected == current and set(expected) == set(task_files):
            return {
                "type": "segment_receipt",
                "review_id": receipt.get("review_id"),
                "segment_id": receipt.get("segment_id"),
            }
    return None


def approved_commit_is_current(root: Path, state: dict[str, Any]) -> bool:
    approved = state.get("approved_snapshot")
    if not isinstance(approved, dict):
        return False
    expected = approved.get("content")
    if not isinstance(expected, dict) or not expected:
        return False
    files = sorted(expected)
    if content_fingerprints(root, files) != expected:
        return False
    status = run_git(["status", "--porcelain", "--", *files], cwd=root, check=False)
    return status.returncode == 0 and not status.stdout.strip()


def simplicity_signals(root: Path, files: list[str]) -> list[str]:
    signals: list[str] = []
    for raw in files:
        path = root / raw
        if not path.is_file() or path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".java", ".go", ".rs"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.count("\n") + 1
        if not is_tracked_in_head(root, raw) and lines > 400:
            signals.append(f"simplicity: new file {raw} has {lines} lines")
    return list(dict.fromkeys(signals))


def latest_review(state: dict[str, Any]) -> dict[str, Any] | None:
    current = state.get("review")
    history = [item for item in state.get("review_history", []) if isinstance(item, dict)]
    candidates = [*history, current] if isinstance(current, dict) else history
    return candidates[-1] if candidates else None


def _shell_tokens(command: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(command, posix=True))
    except ValueError:
        return tuple(command.split())
