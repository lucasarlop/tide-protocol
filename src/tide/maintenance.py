from __future__ import annotations

import shlex
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Sequence

from . import agility as _agility
from . import v1 as _v1
from .locks import matching_locks
from .project import TideError, load_runtime, save_runtime

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Callable[..., Any]] = {}
_ORIGINAL_REQUIRED: Callable[[dict[str, Any], list[Any]], list[str]] | None = None
_ORIGINAL_NEXT_ACTION: Callable[[dict[str, Any], list[dict[str, Any]], list[str]], str] | None = None

_SHELLS = {"sh", "bash", "zsh", "dash", "fish"}
_SHELL_FLAGS = {"-c", "-lc", "-ic"}
_REQUIRED_BLOCKER = "required validations are missing for their covered files"


def install(core: ModuleType) -> None:
    global _CORE, _ORIGINAL_REQUIRED, _ORIGINAL_NEXT_ACTION
    if getattr(core, "_maintenance_1_1_1_installed", False):
        return

    _CORE = core
    for name in ("revise", "preparation_report", "create_review_packet", "check"):
        _ORIGINALS[name] = getattr(core, name)

    _ORIGINAL_REQUIRED = _agility._required_validations
    _ORIGINAL_NEXT_ACTION = _v1._next_action
    _agility._required_validations = _compatible_required_validations
    _v1._next_action = _next_action

    core.revise = revise
    core.preparation_report = preparation_report
    core.create_review_packet = create_review_packet
    core.check = check
    core._maintenance_1_1_1_installed = True


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide maintenance controls are not installed")
    return _CORE


def _shell_tokens(command: str) -> tuple[str, ...]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        return tuple(lexer)
    except (TypeError, ValueError):
        return tuple(command.split())


def canonical_command(command: str | Sequence[Any]) -> tuple[str, ...]:
    if isinstance(command, str):
        return _shell_tokens(command.strip())

    parts = tuple(str(part) for part in command)
    if (
        len(parts) >= 3
        and Path(parts[0]).name in _SHELLS
        and parts[1] in _SHELL_FLAGS
    ):
        return (*_shell_tokens(parts[2]), *parts[3:])
    return parts


def display_command(command: str | Sequence[Any]) -> str:
    if isinstance(command, str):
        return command.strip()
    return " ".join(str(part) for part in command)


def _original_required(runtime: dict[str, Any], locks: list[Any]) -> list[str]:
    if _ORIGINAL_REQUIRED is None:
        raise RuntimeError("Tide required-validation controls are not installed")
    return list(_ORIGINAL_REQUIRED(runtime, locks))


def _passed_commands(runtime: dict[str, Any]) -> list[tuple[str, tuple[str, ...]]]:
    return [
        (display_command(item.get("command", [])), canonical_command(item.get("command", [])))
        for item in runtime.get("validations", [])
        if isinstance(item, dict) and item.get("passed")
    ]


def _compatible_required_validations(
    runtime: dict[str, Any],
    locks: list[Any],
) -> list[str]:
    required = _original_required(runtime, locks)
    passed = _passed_commands(runtime)
    compatible: list[str] = []
    for command in required:
        expected = canonical_command(command)
        match = next((display for display, key in passed if key == expected), None)
        compatible.append(match or command)
    return sorted(dict.fromkeys(compatible))


def _required_status(
    root: Path,
    runtime: dict[str, Any],
    locks: list[Any] | None = None,
) -> list[dict[str, Any]]:
    task_files = _core()._task_files(root, runtime)
    locks = locks if locks is not None else matching_locks(
        root, task_files or runtime.get("boundary", [])
    )
    current = _agility._current_validations(root, runtime)
    passed = [
        (display_command(item.get("command", [])), canonical_command(item.get("command", [])))
        for item in current
        if item.get("passed")
    ]
    status: list[dict[str, Any]] = []
    for command in _original_required(runtime, locks):
        expected = canonical_command(command)
        match = next((display for display, key in passed if key == expected), None)
        status.append(
            {
                "required": command,
                "matched": match is not None,
                "matched_command": match,
            }
        )
    return status


def _missing_required(status: list[dict[str, Any]]) -> list[str]:
    return [str(item["required"]) for item in status if not item.get("matched")]


def _coverage_state(
    root: Path,
    runtime: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    current = _agility._current_validations(root, runtime)
    _, uncovered = _agility._coverage_status(root, runtime, current)
    return current, uncovered


def _deduplicate_validations(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in values:
        key = (
            str(item.get("validation_id") or ""),
            str(item.get("log_id") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def revise(root: Path, **kwargs: Any) -> dict[str, Any]:
    before = load_runtime(root)
    previous = [
        dict(item)
        for item in before.get("validations", [])
        if isinstance(item, dict) and item.get("passed")
    ]

    _ORIGINALS["revise"](root, **kwargs)
    runtime = load_runtime(root)
    task_files = set(_core()._task_files(root, runtime))
    preserved = [
        item
        for item in previous
        if set(str(path) for path in item.get("files", [])) <= task_files
        and _agility._validation_is_current(root, item)
    ]
    current = [
        item
        for item in runtime.get("validations", [])
        if isinstance(item, dict)
    ]
    runtime["validations"] = _deduplicate_validations([*preserved, *current])
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def _store_validation_state(
    root: Path,
    runtime: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    required_status = _required_status(root, runtime)
    missing = _missing_required(required_status)
    current, uncovered = _coverage_state(root, runtime)
    runtime["required_validation_status"] = required_status
    runtime["missing_required_validations"] = missing
    runtime["uncovered_validation_files"] = uncovered
    runtime["current_validation_count"] = len(current)
    runtime["stale_validation_count"] = max(
        0, len(runtime.get("validations", [])) - len(current)
    )
    save_runtime(root, runtime)
    return required_status, missing, uncovered


def _next_action(
    runtime: dict[str, Any],
    blockers: list[dict[str, Any]],
    pending: list[str],
) -> str:
    missing = list(runtime.get("missing_required_validations", []))
    if missing:
        return f"run mandatory validation: {missing[0]}"
    uncovered = list(runtime.get("uncovered_validation_files", []))
    if uncovered:
        return f"validate uncovered files: {', '.join(uncovered[:3])}"
    if _ORIGINAL_NEXT_ACTION is None:
        return "implement the smallest safe delta"
    return _ORIGINAL_NEXT_ACTION(runtime, blockers, pending)


def preparation_report(
    root: Path,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime or load_runtime(root)
    report = _ORIGINALS["preparation_report"](root, runtime)
    runtime = load_runtime(root)
    required_status, missing, uncovered = _store_validation_state(root, runtime)
    report.update(
        {
            "required_validation_status": required_status,
            "missing_required_validations": missing,
            "uncovered_validation_files": uncovered,
            "current_validation_count": runtime.get("current_validation_count", 0),
            "stale_validation_count": runtime.get("stale_validation_count", 0),
        }
    )
    if missing:
        report["next_action"] = f"run mandatory validation: {missing[0]}"
    elif uncovered:
        report["next_action"] = f"validate uncovered files: {', '.join(uncovered[:3])}"
    checkpoint = _v1._checkpoint(root, runtime)
    report["resume"] = checkpoint
    report["lifecycle"] = runtime.get("lifecycle")
    return report


def create_review_packet(root: Path, **kwargs: Any) -> dict[str, Any]:
    try:
        return _ORIGINALS["create_review_packet"](root, **kwargs)
    except TideError as exc:
        runtime = load_runtime(root)
        if not runtime:
            raise
        _, missing, uncovered = _store_validation_state(root, runtime)
        message = str(exc)
        if missing and "mandatory validations" in message:
            raise TideError(
                "review requires mandatory validation: " + "; ".join(missing)
            ) from exc
        if uncovered and "validation coverage" in message:
            raise TideError(
                "review requires validation coverage for: " + ", ".join(uncovered)
            ) from exc
        raise


def _check_next_action(report: dict[str, Any]) -> str:
    missing = list(report.get("missing_required_validations", []))
    if missing:
        return f"run mandatory validation: {missing[0]}"
    uncovered = list(report.get("uncovered_validation_files", []))
    if uncovered:
        return f"validate uncovered files: {', '.join(uncovered[:3])}"
    blockers = [str(value) for value in report.get("blockers", [])]
    if any("blocking findings" in value for value in blockers):
        return "fix only the listed blocking finding, then run targeted validation"
    if any("independent review required" in value for value in blockers):
        return "complete the current review without expanding scope"
    if report.get("ready"):
        return "closure ready"
    return str(report.get("next_action") or "implement the smallest safe delta")


def check(root: Path) -> dict[str, Any]:
    report = _ORIGINALS["check"](root)
    runtime = load_runtime(root)
    if not runtime:
        return report

    required_status, missing, uncovered = _store_validation_state(root, runtime)
    blockers = [
        str(value)
        for value in report.get("blockers", [])
        if str(value) != _REQUIRED_BLOCKER
    ]
    if missing:
        blockers.append(_REQUIRED_BLOCKER)
    blockers = list(dict.fromkeys(blockers))
    pending = list(report.get("pending_hardgates", []))
    ready = not blockers and not pending

    runtime["status"] = "ready" if ready else "blocked"
    save_runtime(root, runtime)

    report.update(
        {
            "ready": ready,
            "status": runtime["status"],
            "blockers": blockers,
            "primary_blocker": blockers[0] if blockers else None,
            "required_validation_status": required_status,
            "missing_validations": missing,
            "missing_required_validations": missing,
            "uncovered_validation_files": uncovered,
            "current_validation_count": runtime.get("current_validation_count", 0),
            "stale_validation_count": runtime.get("stale_validation_count", 0),
        }
    )
    report["next_action"] = _check_next_action(report)
    report["resume"] = _v1._checkpoint(root, runtime)
    report["lifecycle"] = runtime.get("lifecycle")
    return report
