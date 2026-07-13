from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Sequence

from . import agility as _agility
from . import maintenance as _maintenance
from .artifacts import read_review_packet
from .project import TideError, diff_fingerprint, file_fingerprints, load_runtime, save_runtime
from .validation_jobs import read_job

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Callable[..., Any]] = {}
_ORIGINAL_MATCHING_COMMAND: Callable[..., str | None] | None = None


def install(core: ModuleType) -> None:
    global _CORE, _ORIGINAL_MATCHING_COMMAND
    if getattr(core, "_session_stability_installed", False):
        return

    _CORE = core
    for name in (
        "prepare",
        "revise",
        "split",
        "validation_status",
        "validation_wait",
        "validation_log",
        "create_review_packet",
        "submit_review",
    ):
        _ORIGINALS[name] = getattr(core, name)

    _ORIGINAL_MATCHING_COMMAND = _maintenance._matching_command
    _maintenance._matching_command = _matching_command

    core.prepare = prepare
    core.revise = revise
    core.split = split
    core.validation_status = validation_status
    core.validation_wait = validation_wait
    core.validation_log = validation_log
    core.create_review_packet = create_review_packet
    core.submit_review = submit_review
    core._session_stability_installed = True


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide session stability controls are not installed")
    return _CORE


def _path_selector_covers(broad: str, narrow: str) -> bool:
    broad = broad.replace("\\", "/")
    narrow = narrow.replace("\\", "/")
    if broad == narrow:
        return True
    if broad in {".", "./"}:
        return True
    if broad.endswith("/"):
        return narrow.startswith(broad)
    return False


def command_covers(
    passed_command: str | Sequence[Any],
    required_command: str | Sequence[Any],
) -> bool:
    passed = _maintenance.canonical_command(passed_command)
    required = _maintenance.canonical_command(required_command)
    if passed == required:
        return True
    if not passed or not required or passed[0] != required[0]:
        return False

    passed_options = {token for token in passed[1:] if token.startswith("-")}
    required_options = {token for token in required[1:] if token.startswith("-")}
    if not required_options <= passed_options:
        return False

    passed_selectors = [token for token in passed[1:] if not token.startswith("-")]
    required_selectors = [token for token in required[1:] if not token.startswith("-")]
    if not passed_selectors or not required_selectors:
        return False

    return all(
        any(_path_selector_covers(broad, narrow) for broad in passed_selectors)
        for narrow in required_selectors
    )


def _matching_command(
    required: str,
    passed: list[tuple[str, tuple[str, ...]]],
) -> str | None:
    if _ORIGINAL_MATCHING_COMMAND is None:
        raise RuntimeError("Tide command matching is not installed")
    match = _ORIGINAL_MATCHING_COMMAND(required, passed)
    if match is not None:
        return match
    return next(
        (
            display
            for display, canonical in passed
            if command_covers(canonical, required)
        ),
        None,
    )


def _prune_required_validations(runtime: dict[str, Any]) -> bool:
    commands = sorted(
        dict.fromkeys(
            str(command).strip()
            for command in runtime.get("required_validations", [])
            if str(command).strip()
        )
    )
    kept = [
        command
        for command in commands
        if not any(
            other != command and command_covers(other, command)
            for other in commands
        )
    ]
    if kept == commands:
        return False
    runtime["required_validations"] = kept
    return True


def _report_after_runtime_update(root: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        return fallback
    report = _core().preparation_report(root, runtime)
    return {**fallback, **report}


def prepare(
    root: Path,
    task: str,
    files: list[str] | None = None,
    required_validations: list[str] | None = None,
) -> dict[str, Any]:
    result = _ORIGINALS["prepare"](root, task, files, required_validations)
    runtime = load_runtime(root)
    if runtime and _prune_required_validations(runtime):
        save_runtime(root, runtime)
        return _report_after_runtime_update(root, result)
    return result


def revise(root: Path, **kwargs: Any) -> dict[str, Any]:
    result = _ORIGINALS["revise"](root, **kwargs)
    runtime = load_runtime(root)
    if runtime and _prune_required_validations(runtime):
        save_runtime(root, runtime)
        return _report_after_runtime_update(root, result)
    return result


def _narrow_validation(
    root: Path,
    item: dict[str, Any],
    target_files: list[str],
) -> dict[str, Any] | None:
    if not item.get("passed") or not target_files:
        return None

    expected = item.get("coverage_fingerprints")
    current = file_fingerprints(root, target_files)
    if isinstance(expected, dict):
        normalized = {str(path): str(value) for path, value in expected.items()}
        if not set(target_files) <= set(normalized):
            return None
        if {path: normalized[path] for path in target_files} != current:
            return None
    else:
        evidence_files = {str(path) for path in item.get("files", [])}
        if not set(target_files) <= evidence_files:
            return None
        if not _agility._validation_is_current(root, item):
            return None

    narrowed = dict(item)
    narrowed["files"] = list(target_files)
    narrowed["covers"] = list(target_files)
    narrowed["coverage_fingerprints"] = current
    narrowed["diff_fingerprint"] = diff_fingerprint(root, target_files)
    narrowed["inherited_from_parent_segment"] = True
    return narrowed


def _deduplicate_validations(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for item in values:
        key = (
            str(item.get("validation_id") or ""),
            str(item.get("log_id") or ""),
            tuple(sorted(str(path) for path in item.get("files", []))),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def split(root: Path, *, task: str, files: list[str]) -> dict[str, Any]:
    before = load_runtime(root)
    previous = [
        dict(item)
        for item in before.get("validations", [])
        if isinstance(item, dict) and item.get("passed")
    ] if before else []

    result = _ORIGINALS["split"](root, task=task, files=files)
    runtime = load_runtime(root)
    if not runtime:
        return result

    target_files = list(_core()._task_files(root, runtime))
    inherited = [
        narrowed
        for item in previous
        if (narrowed := _narrow_validation(root, item, target_files)) is not None
    ]
    current = [
        item
        for item in runtime.get("validations", [])
        if isinstance(item, dict) and item.get("passed")
    ]
    runtime["validations"] = _deduplicate_validations([*inherited, *current])
    _prune_required_validations(runtime)
    save_runtime(root, runtime)

    report = _core().preparation_report(root, runtime)
    return {
        **result,
        **report,
        "inherited_validation_count": len(inherited),
    }


def _log_id_from_result(root: Path, value: dict[str, Any]) -> str | None:
    if value.get("log_id"):
        return str(value["log_id"])
    evidence = value.get("evidence")
    if isinstance(evidence, dict) and evidence.get("log_id"):
        return str(evidence["log_id"])
    validation_id = str(value.get("validation_id") or "")
    if validation_id:
        try:
            job = read_job(root, validation_id)
        except TideError:
            return None
        evidence = job.get("evidence")
        if isinstance(evidence, dict) and evidence.get("log_id"):
            return str(evidence["log_id"])
    return None


def _failure_summary(content: str) -> list[str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    markers = (
        "FAILED ",
        "ERROR ",
        "AssertionError",
        "Traceback",
        "E   ",
        "short test summary",
        "error:",
        "fatal:",
    )
    selected = [
        line[:500]
        for line in lines
        if any(marker.lower() in line.lower() for marker in markers)
    ]
    if not selected:
        selected = [line[:500] for line in lines[-8:]]
    return list(dict.fromkeys(selected))[:12]


def _enrich_validation_result(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    status = str(result.get("status") or "")
    log_id = _log_id_from_result(root, result)
    if log_id:
        result["log_id"] = log_id

    if status in {"starting", "running"}:
        result.update(
            {
                "next_action": "call validation_wait for this validation_id",
                "user_action_required": False,
                "agent_should_continue": True,
                "authorization_request": None,
            }
        )
        return result

    if status == "completed" and not bool(result.get("passed")):
        if log_id:
            try:
                payload = _ORIGINALS["validation_log"](root, log_id)
                result["failure_summary"] = _failure_summary(str(payload.get("content") or ""))
            except TideError:
                result["failure_summary"] = []
        result.update(
            {
                "next_action": "inspect the failure summary, fix the cause, and rerun only the smallest affected validation",
                "user_action_required": False,
                "agent_should_continue": True,
                "authorization_request": None,
            }
        )
        return result

    if status == "completed":
        try:
            report = _core().preparation_report(root)
            next_action = str(
                (report.get("resume") or {}).get("next_action")
                or report.get("next_action")
                or "continue with Tide check or the next required validation/review"
            )
        except Exception:
            next_action = "continue with Tide check or the next required validation/review"
        result.update(
            {
                "next_action": next_action,
                "user_action_required": False,
                "agent_should_continue": True,
                "authorization_request": None,
            }
        )
    return result


def validation_status(root: Path, validation_id: str) -> dict[str, Any]:
    return _enrich_validation_result(
        root,
        _ORIGINALS["validation_status"](root, validation_id),
    )


def validation_wait(root: Path, validation_id: str, wait_seconds: int = 20) -> dict[str, Any]:
    return _enrich_validation_result(
        root,
        _ORIGINALS["validation_wait"](root, validation_id, wait_seconds),
    )


def validation_log(root: Path, log_id: str) -> dict[str, Any]:
    validation_id: str | None = None
    resolved_log_id = log_id
    if str(log_id).startswith("validation-job-"):
        validation_id = str(log_id)
        status = _ORIGINALS["validation_status"](root, validation_id)
        resolved = _log_id_from_result(root, status)
        if not resolved:
            raise TideError(f"validation job has no saved log yet: {validation_id}")
        resolved_log_id = resolved

    payload = _ORIGINALS["validation_log"](root, resolved_log_id)
    content = str(payload.get("content") or "")
    return {
        **payload,
        "validation_id": validation_id,
        "failure_summary": _failure_summary(content),
    }


def create_review_packet(root: Path, **kwargs: Any) -> dict[str, Any]:
    result = _ORIGINALS["create_review_packet"](root, **kwargs)
    return {
        **result,
        "reviewer_submits_verdict": True,
        "writer_must_not_resubmit": True,
    }


def submit_review(root: Path, **kwargs: Any) -> dict[str, Any]:
    try:
        result = _ORIGINALS["submit_review"](root, **kwargs)
        return {**result, "verdict_submitted": True, "idempotent": False}
    except TideError as exc:
        if "already has a submitted verdict" not in str(exc):
            raise
        packet = read_review_packet(root, str(kwargs.get("review_id") or ""))
        submission = packet.get("submission")
        if not isinstance(submission, dict):
            raise
        return {
            **submission,
            "verdict_submitted": True,
            "idempotent": True,
        }
