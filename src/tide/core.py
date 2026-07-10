from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .commands import run_validation
from .locks import matching_locks
from .policy import decide
from .project import (
    TideError,
    changed_files,
    current_diff,
    diff_fingerprint,
    file_fingerprints,
    load_runtime,
    save_runtime,
)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def prepare(root: Path, task: str, files: list[str] | None = None) -> dict[str, Any]:
    boundary = sorted(dict.fromkeys(files or []))
    locks = matching_locks(root, boundary)
    policy = decide(task, boundary, locks)
    baseline_files = changed_files(root)
    baseline_fingerprints = file_fingerprints(root, baseline_files)
    dirty_boundary = sorted(path for path in baseline_files if _inside(path, boundary))
    hardgates = set(policy.hardgates)
    reasons = list(policy.reasons)
    if dirty_boundary:
        hardgates.add("dirty_boundary")
        reasons.append("pre-existing changes overlap the boundary")

    runtime = {
        "version": 1,
        "task": task,
        "status": "prepared",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "boundary": boundary,
        "baseline_files": baseline_files,
        "baseline_fingerprints": baseline_fingerprints,
        "hardgates": sorted(hardgates),
        "authorized_hardgates": [],
        "review_required": policy.review_required or bool(dirty_boundary),
        "review_reasons": list(dict.fromkeys(reasons)),
        "locks": [lock.name for lock in locks],
        "validations": [],
        "review": None,
    }
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def authorize(
    root: Path,
    gates: list[str] | None = None,
    *,
    all_gates: bool = False,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before authorization")
    known = set(runtime.get("hardgates", []))
    requested = known if all_gates else set(gates or [])
    unknown = sorted(requested - known)
    if unknown:
        raise TideError(f"unknown hardgates: {', '.join(unknown)}")
    authorized = set(runtime.get("authorized_hardgates", [])) | requested
    runtime["authorized_hardgates"] = sorted(authorized)
    runtime["updated_at"] = now_iso()
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def preparation_report(
    root: Path,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime or load_runtime(root)
    boundary = runtime.get("boundary", [])
    locks = matching_locks(root, boundary)
    required_validations = sorted(
        {command for lock in locks for command in lock.validations}
    )
    hardgates = sorted(set(runtime.get("hardgates", [])))
    authorized = sorted(set(runtime.get("authorized_hardgates", [])))
    pending = sorted(set(hardgates) - set(authorized))
    mutation_allowed = bool(boundary) and not pending
    return {
        "task": runtime.get("task"),
        "status": runtime.get("status"),
        "boundary": boundary,
        "boundary_required": not bool(boundary),
        "preexisting_changes": runtime.get("baseline_files", []),
        "hardgates": hardgates,
        "authorized_hardgates": authorized,
        "pending_hardgates": pending,
        "mutation_allowed": mutation_allowed,
        "review_required": runtime.get("review_required", False),
        "review_reasons": runtime.get("review_reasons", []),
        "locks": [
            {
                "name": lock.name,
                "criticality": lock.criticality,
                "paths": list(lock.paths),
                "validations": list(lock.validations),
                "invariants": list(lock.invariants),
                "sensitive_changes": list(lock.sensitive_changes),
            }
            for lock in locks
        ],
        "required_validations": required_validations,
        "rules": {
            "writers": 1,
            "reviewers": 1 if runtime.get("review_required") else 0,
            "commit_requires_supervisor": True,
        },
    }


def record_validation(
    root: Path,
    command: list[str],
    timeout: int = 300,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before validation")
    result = run_validation(root, command, timeout=timeout)
    task_files = _task_files(root, runtime)
    evidence = {
        **result,
        "created_at": now_iso(),
        "files": task_files,
        "diff_fingerprint": diff_fingerprint(root, task_files),
    }
    runtime.setdefault("validations", []).append(evidence)
    runtime["updated_at"] = now_iso()
    save_runtime(root, runtime)
    return evidence


def record_review(
    root: Path,
    *,
    approved: bool,
    findings: list[str],
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before review")
    task_files = _task_files(root, runtime)
    runtime["review"] = {
        "approved": approved,
        "findings": findings,
        "created_at": now_iso(),
        "files": task_files,
        "diff_fingerprint": diff_fingerprint(root, task_files),
    }
    runtime["updated_at"] = now_iso()
    save_runtime(root, runtime)
    return runtime["review"]


def review_packet(root: Path) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before review")
    task_files = _task_files(root, runtime)
    locks = matching_locks(root, task_files or runtime.get("boundary", []))
    outside = _outside_violations(root, runtime)
    fingerprint = diff_fingerprint(root, task_files)
    current_validations = [
        item
        for item in runtime.get("validations", [])
        if item.get("diff_fingerprint") == fingerprint
    ]
    return {
        "task": runtime.get("task"),
        "boundary": runtime.get("boundary", []),
        "files": task_files,
        "outside_boundary": outside,
        "diff_fingerprint": fingerprint,
        "diff": current_diff(root, task_files),
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
        "stale_validation_count": len(runtime.get("validations", [])) - len(current_validations),
        "review_focus": runtime.get("review_reasons", []),
        "instruction": (
            "Read-only review. Return concise blocking and non-blocking findings."
        ),
    }


def check(root: Path) -> dict[str, Any]:
    runtime = load_runtime(root)
    actual = changed_files(root)
    boundary = runtime.get("boundary", []) if runtime else []
    task_files = _task_files(root, runtime) if runtime else actual
    outside = _outside_violations(root, runtime) if runtime else actual
    locks = matching_locks(root, task_files)

    actual_policy = decide(
        str(runtime.get("task", "")) if runtime else "",
        task_files,
        locks,
    )
    stored_hardgates = set(runtime.get("hardgates", [])) if runtime else set()
    hardgates = stored_hardgates | set(actual_policy.hardgates)
    authorized = set(runtime.get("authorized_hardgates", [])) if runtime else set()
    pending_hardgates = sorted(hardgates - authorized)

    current_fingerprint = diff_fingerprint(root, task_files)
    validations = runtime.get("validations", []) if runtime else []
    current_validations = [
        item
        for item in validations
        if item.get("diff_fingerprint") == current_fingerprint
    ]
    passed_commands = {
        " ".join(item.get("command", []))
        for item in current_validations
        if item.get("passed")
    }
    required = sorted({command for lock in locks for command in lock.validations})
    missing_required = [command for command in required if command not in passed_commands]
    failures = [item for item in current_validations if not item.get("passed")]
    stale_validations = len(validations) - len(current_validations)

    review_required = (
        bool(runtime and runtime.get("review_required"))
        or actual_policy.review_required
        or any(lock.review_required for lock in locks)
    )
    review = runtime.get("review") if runtime else None
    review_current = bool(
        review and review.get("diff_fingerprint") == current_fingerprint
    )

    blockers: list[str] = []
    if not runtime:
        blockers.append("no active Tide preparation")
    if task_files and not boundary:
        blockers.append("no boundary declared")
    if outside:
        blockers.append("files changed outside the declared boundary")
    if pending_hardgates:
        blockers.append("hardgates not authorized")
    if task_files and not current_validations:
        blockers.append("no validation recorded for the current diff")
    if failures:
        blockers.append("one or more validations failed for the current diff")
    if missing_required:
        blockers.append("Module Lock validations are missing for the current diff")
    if review_required and not review:
        blockers.append("independent review required")
    elif review_required and not review_current:
        blockers.append("independent review is stale for the current diff")
    elif review and not review.get("approved"):
        blockers.append("independent review has blocking findings")

    ready = not blockers
    if runtime:
        runtime["hardgates"] = sorted(hardgates)
        runtime["review_required"] = review_required
        runtime["review_reasons"] = list(
            dict.fromkeys(
                [
                    *runtime.get("review_reasons", []),
                    *actual_policy.reasons,
                ]
            )
        )
        runtime["status"] = "ready" if ready else "blocked"
        runtime["updated_at"] = now_iso()
        save_runtime(root, runtime)

    return {
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "files": task_files,
        "all_worktree_changes": actual,
        "boundary": boundary,
        "outside_boundary": outside,
        "locks": [lock.name for lock in locks],
        "diff_fingerprint": current_fingerprint,
        "required_validations": required,
        "missing_validations": missing_required,
        "current_validation_count": len(current_validations),
        "stale_validation_count": stale_validations,
        "failed_validation_count": len(failures),
        "review_required": review_required,
        "review_current": review_current,
        "review": review,
        "hardgates": sorted(hardgates),
        "authorized_hardgates": sorted(authorized),
        "pending_hardgates": pending_hardgates,
        "blockers": blockers,
    }


def _task_files(root: Path, runtime: dict[str, Any]) -> list[str]:
    boundary = runtime.get("boundary", [])
    if not boundary:
        return changed_files(root)
    return sorted(
        path for path in changed_files(root) if _inside(path, boundary)
    )


def _outside_violations(root: Path, runtime: dict[str, Any]) -> list[str]:
    boundary = runtime.get("boundary", [])
    if not boundary:
        return changed_files(root)
    baseline = runtime.get("baseline_fingerprints", {})
    violations: list[str] = []
    for path in changed_files(root):
        if _inside(path, boundary):
            continue
        previous = baseline.get(path)
        current = file_fingerprints(root, [path])[path]
        if previous != current:
            violations.append(path)
    return sorted(violations)


def _inside(path: str, boundary: list[str]) -> bool:
    from .locks import _matches

    return any(_matches(path, pattern) for pattern in boundary)
