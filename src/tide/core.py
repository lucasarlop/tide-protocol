from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
from typing import Any

from .artifacts import (
    read_review_packet,
    read_validation_log,
    save_review_packet,
    save_validation_log,
)
from .commands import run_validation
from .locks import matching_locks
from .policy import decide
from .project import (
    TideError,
    changed_files,
    current_diff,
    diff_fingerprint,
    file_fingerprints,
    is_tracked_in_head,
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
        "version": 2,
        "revision": 0,
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


def revise(
    root: Path,
    *,
    task: str | None = None,
    add_files: list[str] | None = None,
    remove_files: list[str] | None = None,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before revise")

    boundary = set(runtime.get("boundary", []))
    boundary.update(add_files or [])
    boundary.difference_update(remove_files or [])
    new_boundary = sorted(boundary)
    if not new_boundary:
        raise TideError("revised boundary cannot be empty")

    new_task = task if task is not None else str(runtime.get("task", ""))
    locks = matching_locks(root, new_boundary)
    policy = decide(new_task, new_boundary, locks)
    baseline_files = list(runtime.get("baseline_files", []))
    dirty_boundary = sorted(path for path in baseline_files if _inside(path, new_boundary))
    hardgates = set(policy.hardgates)
    reasons = list(policy.reasons)
    if dirty_boundary:
        hardgates.add("dirty_boundary")
        reasons.append("pre-existing changes overlap the boundary")

    previously_authorized = set(runtime.get("authorized_hardgates", []))
    runtime.update(
        {
            "task": new_task,
            "status": "revising",
            "updated_at": now_iso(),
            "revision": int(runtime.get("revision", 0)) + 1,
            "boundary": new_boundary,
            "hardgates": sorted(hardgates),
            "authorized_hardgates": sorted(previously_authorized & hardgates),
            "review_required": policy.review_required or bool(dirty_boundary),
            "review_reasons": list(dict.fromkeys(reasons)),
            "locks": [lock.name for lock in locks],
            "validations": [],
            "review": None,
        }
    )
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
        "revision": int(runtime.get("revision", 0)),
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
    log_meta = save_validation_log(root, result)
    task_files = _task_files(root, runtime)
    evidence = {
        "command": list(result.get("command", [])),
        "exit_code": int(result.get("exit_code", 1)),
        "passed": bool(result.get("passed", False)),
        "timed_out": bool(result.get("timed_out", False)),
        "duration_seconds": result.get("duration_seconds"),
        **log_meta,
        "created_at": now_iso(),
        "files": task_files,
        "diff_fingerprint": diff_fingerprint(root, task_files),
    }
    runtime.setdefault("validations", []).append(evidence)
    runtime["updated_at"] = now_iso()
    save_runtime(root, runtime)
    return evidence


def validation_log(root: Path, log_id: str) -> dict[str, Any]:
    return read_validation_log(root, log_id)


def record_review(
    root: Path,
    *,
    approved: bool,
    findings: list[str],
    review_id: str | None = None,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before review")
    task_files = _task_files(root, runtime)
    fingerprint = diff_fingerprint(root, task_files)
    if review_id:
        packet = read_review_packet(root, review_id)
        if packet.get("diff_fingerprint") != fingerprint:
            raise TideError("review packet is stale for the current diff")
    runtime["review"] = {
        "approved": approved,
        "findings": findings,
        "review_id": review_id,
        "created_at": now_iso(),
        "files": task_files,
        "diff_fingerprint": fingerprint,
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
    simplicity = _simplicity_signals(root, task_files)
    focus = list(dict.fromkeys([*runtime.get("review_reasons", []), *simplicity]))
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
        "review_focus": focus,
        "instruction": (
            "Read-only review. Return concise blocking and non-blocking findings. "
            "Check behavior, stability, tests, security, and simplicity only when signaled."
        ),
    }


def create_review_packet(root: Path) -> dict[str, Any]:
    return save_review_packet(root, review_packet(root))


def get_review_packet(root: Path, review_id: str) -> dict[str, Any]:
    packet = read_review_packet(root, review_id)
    runtime = load_runtime(root)
    task_files = _task_files(root, runtime) if runtime else []
    current = diff_fingerprint(root, task_files)
    return {
        **packet,
        "current": packet.get("diff_fingerprint") == current,
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

    simplicity = _simplicity_signals(root, task_files)
    review_required = (
        bool(runtime and runtime.get("review_required"))
        or actual_policy.review_required
        or any(lock.review_required for lock in locks)
        or bool(simplicity)
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
                    *simplicity,
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
        "review_reasons": list(runtime.get("review_reasons", [])) if runtime else list(simplicity),
        "review_current": review_current,
        "review": review,
        "hardgates": sorted(hardgates),
        "authorized_hardgates": sorted(authorized),
        "pending_hardgates": pending_hardgates,
        "blockers": blockers,
    }


def _simplicity_signals(root: Path, files: list[str]) -> list[str]:
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
        if path.suffix.lower() == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(node, "end_lineno", None):
                    size = int(node.end_lineno) - int(node.lineno) + 1
                    if size > 100:
                        signals.append(f"simplicity: function {node.name} in {raw} has {size} lines")
    return list(dict.fromkeys(signals))


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
