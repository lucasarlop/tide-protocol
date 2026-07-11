from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from .artifacts import read_review_packet, save_review_packet
from .locks import matching_locks
from .project import (
    TideError,
    changed_files,
    current_diff,
    diff_fingerprint,
    file_fingerprints,
    load_runtime,
    save_runtime,
)
from .validation_jobs import read_job, save_job

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Any] = {}

BUDGETS: dict[str, dict[str, int]] = {
    "fast": {
        "max_review_cycles": 2,
        "max_scope_expansions": 2,
        "max_boundary_files": 20,
        "max_validation_runs": 12,
        "warn_elapsed_minutes": 90,
    },
    "strict": {
        "max_review_cycles": 3,
        "max_scope_expansions": 3,
        "max_boundary_files": 35,
        "max_validation_runs": 20,
        "warn_elapsed_minutes": 180,
    },
}

STRICT_GATES = {
    "auth",
    "database",
    "dependency",
    "infrastructure",
    "production",
    "public_api",
    "secrets",
}

SEVERITY_ALIASES = {
    "blocking": "blocking",
    "blocker": "blocking",
    "critical": "blocking",
    "high": "blocking",
    "p0": "blocking",
    "p1": "blocking",
    "follow_up": "follow_up",
    "follow-up": "follow_up",
    "medium": "follow_up",
    "p2": "follow_up",
    "info": "info",
    "low": "info",
    "p3": "info",
}


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide agility controls are not installed")
    return _CORE


def install(core: ModuleType) -> None:
    global _CORE
    if getattr(core, "_agility_controls_installed", False):
        return
    _CORE = core
    for name in (
        "prepare",
        "revise",
        "preparation_report",
        "record_validation",
        "start_validation",
        "validation_status",
        "record_review",
        "submit_review",
        "check",
    ):
        _ORIGINALS[name] = getattr(core, name)

    core.prepare = prepare
    core.revise = revise
    core.reopen = reopen
    core.preparation_report = preparation_report
    core.record_validation = record_validation
    core.start_validation = start_validation
    core.validation_status = validation_status
    core.review_packet = review_packet
    core.create_review_packet = create_review_packet
    core.record_review = record_review
    core.submit_review = submit_review
    core.check = check
    core._validation_is_current = _validation_is_current
    core._agility_controls_installed = True


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _elapsed_minutes(runtime: dict[str, Any]) -> int:
    raw = runtime.get("created_at")
    if not isinstance(raw, str):
        return 0
    try:
        created = datetime.fromisoformat(raw)
        now = datetime.now().astimezone()
        if created.tzinfo is None:
            created = created.astimezone()
        return max(0, int((now - created).total_seconds() // 60))
    except ValueError:
        return 0


def _classify_mode(runtime: dict[str, Any]) -> str:
    gates = set(runtime.get("hardgates", [])) - {
        "closure_reopen",
        "dirty_boundary",
        "extended_investigation",
        "scope_expansion",
    }
    if gates & STRICT_GATES or runtime.get("locks"):
        return "strict"
    return "fast"


def _metrics(runtime: dict[str, Any]) -> dict[str, int]:
    value = runtime.setdefault("workflow_metrics", {})
    for key in ("review_cycles", "scope_expansions", "validation_runs", "reopens"):
        value[key] = int(value.get(key, 0))
    return value


def _archive_review(runtime: dict[str, Any], review: dict[str, Any] | None = None) -> None:
    review = review or runtime.get("review")
    if not isinstance(review, dict) or not review.get("review_id"):
        return
    history = runtime.setdefault("review_history", [])
    if any(item.get("review_id") == review.get("review_id") for item in history if isinstance(item, dict)):
        return
    history.append(review)


def _budget_state(runtime: dict[str, Any]) -> dict[str, Any]:
    mode = str(runtime.get("mode") or _classify_mode(runtime))
    budget = BUDGETS.get(mode, BUDGETS["fast"])
    metrics = _metrics(runtime)
    boundary_count = len(runtime.get("boundary", []))
    elapsed = _elapsed_minutes(runtime)
    reasons: list[str] = []
    if metrics["review_cycles"] > budget["max_review_cycles"]:
        reasons.append("review cycle budget exceeded")
    if metrics["scope_expansions"] > budget["max_scope_expansions"]:
        reasons.append("scope expansion budget exceeded")
    if boundary_count > budget["max_boundary_files"]:
        reasons.append("task boundary is too large")

    warnings: list[str] = []
    if metrics["validation_runs"] > budget["max_validation_runs"]:
        warnings.append("validation count is high; run only checks affected by the latest delta")
    if elapsed > budget["warn_elapsed_minutes"]:
        warnings.append("task has been active too long; converge or split it")
    if metrics["review_cycles"] == budget["max_review_cycles"]:
        warnings.append("review budget is at its limit; only blocking findings should remain in this task")

    return {
        "mode": mode,
        "budget": dict(budget),
        "metrics": {
            **metrics,
            "boundary_files": boundary_count,
            "elapsed_minutes": elapsed,
        },
        "split_required": bool(reasons),
        "split_reasons": reasons,
        "closure_warning": "; ".join(warnings) if warnings else None,
    }


def _apply_budget(runtime: dict[str, Any]) -> dict[str, Any]:
    runtime["mode"] = str(runtime.get("mode") or _classify_mode(runtime))
    state = _budget_state(runtime)
    hardgates = set(runtime.get("hardgates", []))
    authorized = set(runtime.get("authorized_hardgates", []))
    reasons = list(runtime.get("review_reasons", []))
    if state["split_required"]:
        hardgates.add("extended_investigation")
        reasons.extend(state["split_reasons"])
    else:
        hardgates.discard("extended_investigation")
        authorized.discard("extended_investigation")
    runtime["hardgates"] = sorted(hardgates)
    runtime["authorized_hardgates"] = sorted(authorized & hardgates)
    runtime["review_reasons"] = list(dict.fromkeys(reasons))
    runtime["split_required"] = state["split_required"]
    runtime["split_reasons"] = state["split_reasons"]
    runtime["closure_warning"] = state["closure_warning"]
    return state


def _ensure_defaults(runtime: dict[str, Any]) -> None:
    runtime.setdefault("mode", _classify_mode(runtime))
    runtime.setdefault("closure_locked", False)
    runtime.setdefault("closure_reason", None)
    runtime.setdefault("review_history", [])
    runtime.setdefault("follow_up_tasks", [])
    runtime.setdefault("split_required", False)
    runtime.setdefault("split_reasons", [])
    runtime.setdefault("closure_warning", None)
    _metrics(runtime)


def prepare(
    root: Path,
    task: str,
    files: list[str] | None = None,
    required_validations: list[str] | None = None,
) -> dict[str, Any]:
    _ORIGINALS["prepare"](root, task, files, required_validations)
    runtime = load_runtime(root)
    _ensure_defaults(runtime)
    runtime["mode"] = _classify_mode(runtime)
    runtime["workflow_metrics"] = {
        "review_cycles": 0,
        "scope_expansions": 0,
        "validation_runs": 0,
        "reopens": 0,
    }
    runtime["review_history"] = []
    runtime["follow_up_tasks"] = []
    runtime["closure_locked"] = False
    runtime["closure_reason"] = None
    _apply_budget(runtime)
    runtime["updated_at"] = _now_iso()
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def revise(
    root: Path,
    *,
    task: str | None = None,
    add_files: list[str] | None = None,
    remove_files: list[str] | None = None,
    add_required_validations: list[str] | None = None,
    remove_required_validations: list[str] | None = None,
) -> dict[str, Any]:
    before = load_runtime(root)
    if not before:
        raise TideError("run tide prepare before revise")
    _ensure_defaults(before)
    if before.get("closure_locked"):
        raise TideError("closure is locked; use reopen and obtain closure_reopen authorization")

    old_boundary = set(before.get("boundary", []))
    requested_additions = set(add_files or []) - old_boundary
    validation_plan_changed = bool(add_required_validations or remove_required_validations)
    previous_validations = list(before.get("validations", []))
    previous_history = list(before.get("review_history", []))
    previous_followups = list(before.get("follow_up_tasks", []))
    previous_metrics = dict(_metrics(before))
    _archive_review(before)
    previous_history = list(before.get("review_history", []))

    _ORIGINALS["revise"](
        root,
        task=task,
        add_files=add_files,
        remove_files=remove_files,
        add_required_validations=add_required_validations,
        remove_required_validations=remove_required_validations,
    )
    runtime = load_runtime(root)
    _ensure_defaults(runtime)
    runtime["mode"] = "strict" if before.get("mode") == "strict" else _classify_mode(runtime)
    runtime["review_history"] = previous_history
    runtime["follow_up_tasks"] = previous_followups
    runtime["workflow_metrics"] = previous_metrics
    if requested_additions:
        _metrics(runtime)["scope_expansions"] += 1
    runtime["validations"] = [] if validation_plan_changed else previous_validations
    runtime["review"] = None
    runtime["closure_locked"] = False
    runtime["closure_reason"] = None
    _apply_budget(runtime)
    runtime["updated_at"] = _now_iso()
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def reopen(root: Path, *, reason: str) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before reopening")
    reason = reason.strip()
    if not reason:
        raise TideError("reopen requires a concrete blocking reason")
    _ensure_defaults(runtime)
    _archive_review(runtime)
    runtime["review"] = None
    runtime["closure_locked"] = False
    runtime["closure_reason"] = reason
    runtime["status"] = "blocked"
    hardgates = set(runtime.get("hardgates", []))
    hardgates.add("closure_reopen")
    authorized = set(runtime.get("authorized_hardgates", []))
    authorized.discard("closure_reopen")
    runtime["hardgates"] = sorted(hardgates)
    runtime["authorized_hardgates"] = sorted(authorized)
    _metrics(runtime)["reopens"] += 1
    runtime["updated_at"] = _now_iso()
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def preparation_report(
    root: Path,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime or load_runtime(root)
    _ensure_defaults(runtime)
    state = _apply_budget(runtime)
    save_runtime(root, runtime)
    report = _ORIGINALS["preparation_report"](root, runtime)
    pending = set(report.get("pending_hardgates", []))
    closure_locked = bool(runtime.get("closure_locked"))
    report.update(
        {
            "mode": state["mode"],
            "workflow_budget": state["budget"],
            "workflow_metrics": state["metrics"],
            "split_required": state["split_required"],
            "split_reasons": state["split_reasons"],
            "closure_warning": state["closure_warning"],
            "closure_locked": closure_locked,
            "closure_reason": runtime.get("closure_reason"),
            "follow_up_tasks": list(runtime.get("follow_up_tasks", [])),
            "validation_allowed": True,
        }
    )
    report["mutation_allowed"] = bool(report.get("mutation_allowed")) and not closure_locked
    if state["split_required"] and "extended_investigation" not in pending:
        report["next_action"] = "finish the current bounded change; do not expand scope"
    elif state["split_required"]:
        report["next_action"] = "split the task or obtain explicit extended_investigation authorization"
    elif closure_locked:
        report["next_action"] = "run only final validations and tide check"
    elif pending:
        report["next_action"] = "obtain supervisor authorization for pending hardgates"
    else:
        report["next_action"] = "implement the smallest safe delta"
    return report


def _resolve_coverage(
    root: Path,
    runtime: dict[str, Any],
    covers: list[str] | None,
) -> list[str]:
    task_files = _core()._task_files(root, runtime)
    patterns = [value for value in (covers or []) if isinstance(value, str) and value.strip()]
    if not patterns:
        return task_files
    selected = sorted(path for path in task_files if _core()._inside(path, patterns))
    if not selected:
        raise TideError("validation coverage does not match any changed file in the task")
    return selected


def _patch_validation_evidence(
    root: Path,
    evidence: dict[str, Any],
    *,
    files: list[str],
    patterns: list[str] | None,
    phase: str,
) -> dict[str, Any]:
    evidence["files"] = list(files)
    evidence["covers"] = list(patterns or files)
    evidence["coverage_fingerprints"] = file_fingerprints(root, files)
    evidence["diff_fingerprint"] = diff_fingerprint(root, files)
    evidence["phase"] = phase
    return evidence


def record_validation(
    root: Path,
    command: list[str],
    timeout: int = 300,
    *,
    covers: list[str] | None = None,
    phase: str = "targeted",
) -> dict[str, Any]:
    if phase not in {"targeted", "final"}:
        raise TideError("validation phase must be targeted or final")
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before validation")
    _ensure_defaults(runtime)
    files = _resolve_coverage(root, runtime, covers)
    result = _ORIGINALS["record_validation"](root, command, timeout)
    runtime = load_runtime(root)
    for item in reversed(runtime.get("validations", [])):
        if item.get("log_id") == result.get("log_id"):
            result = _patch_validation_evidence(
                root,
                item,
                files=files,
                patterns=covers,
                phase=phase,
            )
            break
    _metrics(runtime)["validation_runs"] += 1
    _apply_budget(runtime)
    runtime["updated_at"] = _now_iso()
    save_runtime(root, runtime)
    return result


def start_validation(
    root: Path,
    command: list[str],
    timeout: int = 300,
    *,
    covers: list[str] | None = None,
    phase: str = "targeted",
) -> dict[str, Any]:
    if phase not in {"targeted", "final"}:
        raise TideError("validation phase must be targeted or final")
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before validation")
    _ensure_defaults(runtime)
    files = _resolve_coverage(root, runtime, covers)
    result = _ORIGINALS["start_validation"](root, command, timeout)
    validation_id = str(result.get("validation_id") or "")
    job = read_job(root, validation_id)
    job["files"] = files
    job["covers"] = list(covers or files)
    job["coverage_fingerprints"] = file_fingerprints(root, files)
    job["diff_fingerprint"] = diff_fingerprint(root, files)
    job["phase"] = phase
    save_job(root, job)
    _metrics(runtime)["validation_runs"] += 1
    _apply_budget(runtime)
    runtime["updated_at"] = _now_iso()
    save_runtime(root, runtime)
    return {**result, "covers": job["covers"], "phase": phase}


def validation_status(root: Path, validation_id: str) -> dict[str, Any]:
    result = _ORIGINALS["validation_status"](root, validation_id)
    job = read_job(root, validation_id)
    if job.get("recorded"):
        runtime = load_runtime(root)
        for item in runtime.get("validations", []):
            if item.get("validation_id") == validation_id:
                item["covers"] = list(job.get("covers") or job.get("files") or [])
                item["coverage_fingerprints"] = dict(
                    job.get("coverage_fingerprints") or file_fingerprints(root, list(job.get("files") or []))
                )
                item["files"] = list(job.get("files") or [])
                item["phase"] = str(job.get("phase") or "targeted")
                job["evidence"] = item
                save_job(root, job)
                save_runtime(root, runtime)
                result["evidence"] = item
                break
    result["covers"] = list(job.get("covers") or job.get("files") or [])
    result["phase"] = str(job.get("phase") or "targeted")
    return result


def _validation_is_current(root: Path, item: dict[str, Any]) -> bool:
    fingerprints = item.get("coverage_fingerprints")
    if isinstance(fingerprints, dict):
        paths = sorted(str(path) for path in fingerprints)
        return fingerprints == file_fingerprints(root, paths)
    files = list(item.get("files") or [])
    return item.get("diff_fingerprint") == diff_fingerprint(root, files)


def _current_validations(root: Path, runtime: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in runtime.get("validations", [])
        if isinstance(item, dict) and _validation_is_current(root, item)
    ]


def _required_validations(runtime: dict[str, Any], locks: list[Any]) -> list[str]:
    return _core()._required_validations(runtime, locks)


def _coverage_status(
    root: Path,
    runtime: dict[str, Any],
    current_validations: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    task_files = _core()._task_files(root, runtime)
    covered: set[str] = set()
    for item in current_validations:
        if item.get("passed"):
            covered.update(str(path) for path in item.get("files", []))
    return task_files, sorted(set(task_files) - covered)


def _normalize_findings(
    findings: list[Any],
    *,
    approved: bool,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in findings:
        if isinstance(item, dict):
            message = str(item.get("message") or "").strip()
            severity_raw = str(item.get("severity") or "").strip().lower()
            severity = SEVERITY_ALIASES.get(severity_raw)
            if not message or not severity:
                raise TideError("structured findings require severity and message")
        else:
            message = str(item).strip()
            if not message:
                continue
            prefix = message.split(":", 1)[0].strip().lower().strip("[]")
            severity = SEVERITY_ALIASES.get(prefix, "info" if approved else "blocking")
        normalized.append({"severity": severity, "message": message})
    return normalized


def _finding_groups(findings: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    return {
        severity: [item for item in findings if item.get("severity") == severity]
        for severity in ("blocking", "follow_up", "info")
    }


def _latest_review(runtime: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [
        item
        for item in [*runtime.get("review_history", []), runtime.get("review")]
        if isinstance(item, dict) and item.get("review_id")
    ]
    return candidates[-1] if candidates else None


def review_packet(root: Path, *, full: bool = False) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before review")
    _ensure_defaults(runtime)
    state = _apply_budget(runtime)
    authorized = set(runtime.get("authorized_hardgates", []))
    if state["split_required"] and "extended_investigation" not in authorized:
        save_runtime(root, runtime)
        raise TideError("task is no longer converging; split it or authorize extended_investigation")

    task_files = _core()._task_files(root, runtime)
    locks = matching_locks(root, task_files or runtime.get("boundary", []))
    current_validations = _current_validations(root, runtime)
    task_files, uncovered = _coverage_status(root, runtime, current_validations)
    passed_commands = {
        " ".join(item.get("command", []))
        for item in current_validations
        if item.get("passed")
    }
    required = _required_validations(runtime, locks)
    missing_required = [command for command in required if command not in passed_commands]
    if task_files and uncovered:
        raise TideError("review requires current passing validation coverage for every changed task file")
    if missing_required:
        raise TideError("review requires all mandatory validations to be current")

    current_fingerprints = file_fingerprints(root, task_files)
    previous = _latest_review(runtime)
    previous_fingerprints = previous.get("file_fingerprints", {}) if previous else {}
    if full or not previous_fingerprints:
        review_files = task_files
        review_mode = "full"
    else:
        review_files = sorted(
            path
            for path in task_files
            if previous_fingerprints.get(path) != current_fingerprints.get(path)
        )
        review_mode = "incremental"
    if not review_files:
        raise TideError("no changed files remain since the latest review")

    previous_findings = list(previous.get("findings", [])) if previous else []
    previous_blocking = [
        item.get("message")
        for item in previous_findings
        if isinstance(item, dict) and item.get("severity") == "blocking"
    ]
    simplicity = _core()._simplicity_signals(root, review_files)
    focus = list(
        dict.fromkeys(
            [
                *runtime.get("review_reasons", []),
                *(f"previous blocker: {message}" for message in previous_blocking if message),
                *simplicity,
            ]
        )
    )
    fingerprint = diff_fingerprint(root, task_files)
    return {
        "task": runtime.get("task"),
        "mode": runtime.get("mode"),
        "review_mode": review_mode,
        "review_base_id": previous.get("review_id") if previous else None,
        "boundary": runtime.get("boundary", []),
        "full_task_files": task_files,
        "files": review_files,
        "outside_boundary": _core()._outside_violations(root, runtime),
        "diff_fingerprint": fingerprint,
        "file_fingerprints": current_fingerprints,
        "diff": current_diff(root, review_files),
        "locks": [
            {
                "name": lock.name,
                "criticality": lock.criticality,
                "invariants": list(lock.invariants),
                "validations": list(lock.validations),
                "sensitive_changes": list(lock.sensitive_changes),
                "contract": lock.body,
            }
            for lock in locks
        ],
        "validations": current_validations,
        "required_validations": required,
        "missing_validations": missing_required,
        "uncovered_validation_files": uncovered,
        "stale_validation_count": len(runtime.get("validations", [])) - len(current_validations),
        "previous_findings": previous_findings,
        "review_focus": focus,
        "instruction": (
            "Review only the supplied delta. Classify every finding as blocking, follow_up, or info. "
            "Only behavior, data loss, security, contract, regression, or indispensable validation gaps are blocking. "
            "Submit directly with review_submit. Do not expand the task for follow-up improvements."
        ),
    }


def create_review_packet(root: Path, *, full: bool = False) -> dict[str, Any]:
    packet = review_packet(root, full=full)
    summary = save_review_packet(root, packet)
    return {
        **summary,
        "review_mode": packet["review_mode"],
        "review_base_id": packet.get("review_base_id"),
        "full_task_file_count": len(packet.get("full_task_files", [])),
    }


def _finalize_review(
    root: Path,
    review: dict[str, Any],
    *,
    review_id: str | None,
    findings: list[dict[str, str]],
) -> dict[str, Any]:
    runtime = load_runtime(root)
    _ensure_defaults(runtime)
    packet = read_review_packet(root, review_id) if review_id else {}
    groups = _finding_groups(findings)
    task_files = _core()._task_files(root, runtime)
    review.update(
        {
            "findings": findings,
            "blocking_findings": groups["blocking"],
            "follow_up_findings": groups["follow_up"],
            "info_findings": groups["info"],
            "approved": not bool(groups["blocking"]),
            "reviewed_files": list(packet.get("files") or task_files),
            "review_mode": packet.get("review_mode", "full"),
            "file_fingerprints": file_fingerprints(root, task_files),
        }
    )
    _metrics(runtime)["review_cycles"] += 1
    review["review_cycle"] = _metrics(runtime)["review_cycles"]
    runtime["review"] = review
    _archive_review(runtime, review)
    followups = list(runtime.get("follow_up_tasks", []))
    for item in groups["follow_up"]:
        if item["message"] not in followups:
            followups.append(item["message"])
    runtime["follow_up_tasks"] = followups
    runtime["closure_locked"] = review["approved"]
    runtime["closure_reason"] = "approved review; only final validation and check remain" if review["approved"] else None
    _apply_budget(runtime)
    runtime["updated_at"] = _now_iso()
    save_runtime(root, runtime)
    return runtime["review"]


def record_review(
    root: Path,
    *,
    approved: bool,
    findings: list[Any],
    review_id: str | None = None,
) -> dict[str, Any]:
    normalized = _normalize_findings(findings, approved=approved)
    effective_approved = not any(item["severity"] == "blocking" for item in normalized)
    review = _ORIGINALS["record_review"](
        root,
        approved=effective_approved,
        findings=normalized,
        review_id=review_id,
    )
    return _finalize_review(
        root,
        review,
        review_id=review_id,
        findings=normalized,
    )


def submit_review(
    root: Path,
    *,
    review_id: str,
    submission_token: str,
    approved: bool,
    findings: list[Any],
) -> dict[str, Any]:
    normalized = _normalize_findings(findings, approved=approved)
    effective_approved = not any(item["severity"] == "blocking" for item in normalized)
    review = _ORIGINALS["submit_review"](
        root,
        review_id=review_id,
        submission_token=submission_token,
        approved=effective_approved,
        findings=normalized,
    )
    return _finalize_review(
        root,
        review,
        review_id=review_id,
        findings=normalized,
    )


def check(root: Path) -> dict[str, Any]:
    report = _ORIGINALS["check"](root)
    runtime = load_runtime(root)
    if not runtime:
        return report
    _ensure_defaults(runtime)
    state = _apply_budget(runtime)
    task_files = _core()._task_files(root, runtime)
    locks = matching_locks(root, task_files)
    validations = list(runtime.get("validations", []))
    current_validations = _current_validations(root, runtime)
    task_files, uncovered = _coverage_status(root, runtime, current_validations)
    failures = [item for item in current_validations if not item.get("passed")]
    passed_commands = {
        " ".join(item.get("command", []))
        for item in current_validations
        if item.get("passed")
    }
    required = _required_validations(runtime, locks)
    missing_required = [command for command in required if command not in passed_commands]

    blockers = [
        blocker
        for blocker in report.get("blockers", [])
        if blocker
        not in {
            "no validation recorded for the current diff",
            "one or more validations failed for the current diff",
            "required validations are missing for the current diff",
            "independent review has blocking findings",
        }
    ]
    if task_files and not current_validations:
        blockers.append("no current validation evidence covers the changed task files")
    if uncovered:
        blockers.append("changed files lack current validation coverage")
    if failures:
        blockers.append("one or more current validations failed")
    if missing_required:
        blockers.append("required validations are missing for their covered files")

    review = runtime.get("review")
    blocking_findings = []
    if isinstance(review, dict):
        blocking_findings = list(review.get("blocking_findings") or [])
        if not blocking_findings:
            blocking_findings = [
                item
                for item in review.get("findings", [])
                if isinstance(item, dict) and item.get("severity") == "blocking"
            ]
    if blocking_findings:
        blockers.append("independent review has blocking findings")

    authorized = set(runtime.get("authorized_hardgates", []))
    if state["split_required"] and "extended_investigation" not in authorized:
        blockers.append("task must be split or extended investigation explicitly authorized")

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    runtime["status"] = "ready" if ready else "blocked"
    runtime["updated_at"] = _now_iso()
    save_runtime(root, runtime)
    report.update(
        {
            "ready": ready,
            "status": runtime["status"],
            "files": task_files,
            "blockers": blockers,
            "mode": state["mode"],
            "workflow_budget": state["budget"],
            "workflow_metrics": state["metrics"],
            "split_required": state["split_required"],
            "split_reasons": state["split_reasons"],
            "closure_warning": state["closure_warning"],
            "closure_locked": bool(runtime.get("closure_locked")),
            "follow_up_tasks": list(runtime.get("follow_up_tasks", [])),
            "required_validations": required,
            "missing_validations": missing_required,
            "current_validation_count": len(current_validations),
            "stale_validation_count": len(validations) - len(current_validations),
            "failed_validation_count": len(failures),
            "uncovered_validation_files": uncovered,
            "current_final_validation_count": len(
                [item for item in current_validations if item.get("phase") == "final" and item.get("passed")]
            ),
        }
    )
    return report
