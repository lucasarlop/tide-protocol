from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .artifacts import read_validation_log, save_validation_log
from .commands import run_validation
from .evidence import evidence_is_current
from .project import TideError, diff_fingerprint, file_fingerprints, load_runtime, save_runtime
from .rules import _inside, _normalize_strings, _task_files, evaluate_state
from .state import now_iso
from .validation_jobs import compact_job, read_job, refresh_job, save_job, start_job

def record_validation(
    root: Path,
    command: list[str],
    timeout: int = 300,
    *,
    covers: list[str] | None = None,
    phase: str = "targeted",
) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before validation")
    if phase not in {"targeted", "final"}:
        raise TideError("validation phase must be targeted or final")
    files = _resolve_coverage(root, state, covers)
    if phase == "final":
        reusable = _reusable_final(root, state, command, files)
        if reusable:
            return {**reusable, "reused": True}
    result = run_validation(root, command, timeout=timeout)
    return _record_validation_result(root, state, result, files=files, phase=phase)


def start_validation(
    root: Path,
    command: list[str],
    timeout: int = 300,
    *,
    covers: list[str] | None = None,
    phase: str = "targeted",
) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before validation")
    if phase not in {"targeted", "final"}:
        raise TideError("validation phase must be targeted or final")
    files = _resolve_coverage(root, state, covers)
    if phase == "final":
        reusable = _reusable_final(root, state, command, files)
        if reusable:
            return {**reusable, "reused": True}
    result = start_job(
        root,
        command=command,
        timeout=timeout,
        files=files,
        diff_fingerprint=diff_fingerprint(root, files),
        revision=int(state.get("revision", 0)),
        created_at=now_iso(),
    )
    validation_id = str(result.get("validation_id") or "")
    job = read_job(root, validation_id)
    job["files"] = files
    job["covers"] = list(covers or files)
    job["coverage_fingerprints"] = file_fingerprints(root, files)
    job["phase"] = phase
    save_job(root, job)
    return _enrich_validation_result(root, {**result, "covers": job["covers"], "phase": phase})


def validation_status(root: Path, validation_id: str) -> dict[str, Any]:
    job = refresh_job(root, validation_id)
    if job.get("status") == "completed" and not job.get("recorded"):
        result = job.get("result")
        if not isinstance(result, dict):
            raise TideError("completed validation job has no result")
        state = load_runtime(root)
        evidence = _record_validation_result(
            root,
            state,
            result,
            files=list(job.get("files") or []),
            phase=str(job.get("phase") or "targeted"),
            validation_id=validation_id,
            coverage_fingerprints=dict(job.get("coverage_fingerprints") or {}),
        )
        job["recorded"] = True
        job["evidence"] = evidence
        save_job(root, job)
    value = compact_job(read_job(root, validation_id))
    latest = read_job(root, validation_id)
    value["covers"] = list(latest.get("covers") or latest.get("files") or [])
    value["phase"] = str(latest.get("phase") or "targeted")
    return _enrich_validation_result(root, value)


def validation_wait(root: Path, validation_id: str, wait_seconds: int = 20) -> dict[str, Any]:
    deadline = time.monotonic() + max(1, min(int(wait_seconds), 60))
    while True:
        result = validation_status(root, validation_id)
        if result.get("status") == "completed":
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {
                **result,
                "passed": None,
                "poll_after_seconds": min(30, max(5, int(wait_seconds))),
                "next_action": "call validation_wait again for this validation_id",
                "agent_should_continue": True,
                "user_action_required": False,
            }
        time.sleep(min(0.5, remaining))


def validation_log(root: Path, log_id: str) -> dict[str, Any]:
    validation_id: str | None = None
    resolved = log_id
    if str(log_id).startswith("validation-job-"):
        validation_id = str(log_id)
        status = validation_status(root, validation_id)
        resolved = str(status.get("log_id") or "")
        if not resolved:
            raise TideError(f"validation job has no saved log yet: {validation_id}")
    payload = read_validation_log(root, resolved)
    return {
        **payload,
        "validation_id": validation_id,
        "failure_summary": _failure_summary(str(payload.get("content") or "")),
    }


def _resolve_coverage(root: Path, state: dict[str, Any], covers: list[str] | None) -> list[str]:
    task_files = _task_files(root, state)
    if not task_files:
        raise TideError("validation requires changed files inside the task boundary")
    patterns = _normalize_strings(covers)
    if not patterns:
        return task_files
    selected = sorted(path for path in task_files if _inside(path, patterns))
    if not selected:
        raise TideError("validation coverage does not match any changed file in the task")
    return selected


def _record_validation_result(
    root: Path,
    state: dict[str, Any],
    result: dict[str, Any],
    *,
    files: list[str],
    phase: str,
    validation_id: str | None = None,
    coverage_fingerprints: dict[str, str] | None = None,
) -> dict[str, Any]:
    if validation_id:
        existing = next(
            (item for item in state.get("validations", []) if item.get("validation_id") == validation_id),
            None,
        )
        if existing:
            return existing
    log_meta = save_validation_log(root, result)
    evidence = {
        "command": list(result.get("command", [])),
        "exit_code": int(result.get("exit_code", 1)),
        "passed": bool(result.get("passed", False)),
        "timed_out": bool(result.get("timed_out", False)),
        "duration_seconds": result.get("duration_seconds"),
        **log_meta,
        "created_at": now_iso(),
        "files": list(files),
        "covers": list(files),
        "coverage_fingerprints": coverage_fingerprints or file_fingerprints(root, files),
        "diff_fingerprint": diff_fingerprint(root, files),
        "phase": phase,
    }
    if validation_id:
        evidence["validation_id"] = validation_id
    state.setdefault("validations", []).append(evidence)
    convergence_value = state.setdefault("convergence", {})
    if evidence["passed"]:
        if convergence_value.get("root_cause_known") is True or convergence_value.get("status") == "progressing":
            convergence_value["failed_attempts"] = 0
            convergence_value["cycle_active"] = False
            convergence_value["status"] = "progressing"
    elif phase == "targeted":
        convergence_value["failed_attempts"] = int(convergence_value.get("failed_attempts", 0)) + 1
        if convergence_value.get("cycle_active"):
            convergence_value["failed_attempts"] = max(2, int(convergence_value["failed_attempts"]))
        if int(convergence_value["failed_attempts"]) >= 2 and convergence_value.get("root_cause_known") is not True:
            convergence_value["status"] = "investigating"
            convergence_value["next_step"] = (
                "stop editing; reproduce the failure minimally and identify the first incorrect state transition"
            )
    state["approved_snapshot"] = None
    state["lifecycle"] = "active"
    save_runtime(root, state)
    return evidence


def _reusable_final(root: Path, state: dict[str, Any], command: list[str], files: list[str]) -> dict[str, Any] | None:
    for item in reversed(state.get("validations", [])):
        if item.get("phase") != "final" or list(item.get("command") or []) != list(command):
            continue
        if sorted(item.get("files") or []) != sorted(files):
            continue
        if item.get("passed") and evidence_is_current(root, item):
            return item
    return None


def _enrich_validation_result(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    evidence = result.get("evidence")
    if isinstance(evidence, dict):
        result.setdefault("log_id", evidence.get("log_id"))
    validation_id = str(result.get("validation_id") or "")
    if validation_id and not result.get("log_id"):
        try:
            job = read_job(root, validation_id)
        except TideError:
            job = {}
        evidence = job.get("evidence")
        if isinstance(evidence, dict):
            result["log_id"] = evidence.get("log_id")
    status = str(result.get("status") or "")
    if status in {"starting", "running"}:
        result.update(
            {
                "passed": None,
                "next_action": "call validation_wait for this validation_id",
                "agent_should_continue": True,
                "user_action_required": False,
            }
        )
    elif status == "completed" and not bool(result.get("passed")):
        log_id = result.get("log_id")
        if log_id:
            payload = read_validation_log(root, str(log_id))
            result["failure_summary"] = _failure_summary(str(payload.get("content") or ""))
        result.update(
            {
                "next_action": "inspect the failure summary, fix the cause, and rerun only the smallest affected validation",
                "agent_should_continue": True,
                "user_action_required": False,
            }
        )
    elif status == "completed":
        evaluation = evaluate_state(root)
        result.update(
            {
                "next_action": evaluation.get("next_action"),
                "agent_should_continue": evaluation.get("agent_should_continue"),
                "user_action_required": evaluation.get("user_action_required"),
            }
        )
    return result


def _failure_summary(content: str) -> list[str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    markers = ("FAILED ", "ERROR ", "AssertionError", "Traceback", "E   ", "error:", "fatal:")
    selected = [
        line[:500]
        for line in lines
        if any(marker.lower() in line.lower() for marker in markers)
    ]
    if not selected:
        selected = [line[:500] for line in lines[-8:]]
    return list(dict.fromkeys(selected))[:12]
