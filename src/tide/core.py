from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .commands import run_validation
from .locks import matching_locks
from .policy import decide
from .project import changed_files, current_diff, load_runtime, save_runtime


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def prepare(root: Path, task: str, files: list[str] | None = None) -> dict[str, Any]:
    boundary = sorted(dict.fromkeys(files or []))
    locks = matching_locks(root, boundary)
    policy = decide(task, boundary, locks)
    runtime = {
        "version": 1,
        "task": task,
        "status": "prepared",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "boundary": boundary,
        "hardgates": list(policy.hardgates),
        "authorized_hardgates": [],
        "review_required": policy.review_required,
        "review_reasons": list(policy.reasons),
        "locks": [lock.name for lock in locks],
        "validations": [],
        "review": None,
    }
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def authorize(root: Path, gates: list[str] | None = None, *, all_gates: bool = False) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise RuntimeError("run tide prepare before authorization")
    known = set(runtime.get("hardgates", []))
    requested = known if all_gates else set(gates or [])
    unknown = sorted(requested - known)
    if unknown:
        raise RuntimeError(f"unknown hardgates: {', '.join(unknown)}")
    authorized = set(runtime.get("authorized_hardgates", [])) | requested
    runtime["authorized_hardgates"] = sorted(authorized)
    runtime["updated_at"] = now_iso()
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def preparation_report(root: Path, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = runtime or load_runtime(root)
    boundary = runtime.get("boundary", [])
    locks = matching_locks(root, boundary)
    required_validations = sorted({command for lock in locks for command in lock.validations})
    hardgates = sorted(set(runtime.get("hardgates", [])))
    authorized = sorted(set(runtime.get("authorized_hardgates", [])))
    pending = sorted(set(hardgates) - set(authorized))
    mutation_allowed = bool(boundary) and not pending
    return {
        "task": runtime.get("task"),
        "status": runtime.get("status"),
        "boundary": boundary,
        "boundary_required": not bool(boundary),
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


def record_validation(root: Path, command: list[str], timeout: int = 300) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise RuntimeError("run tide prepare before validation")
    result = run_validation(root, command, timeout=timeout)
    runtime.setdefault("validations", []).append({**result, "created_at": now_iso()})
    runtime["updated_at"] = now_iso()
    save_runtime(root, runtime)
    return result


def record_review(root: Path, *, approved: bool, findings: list[str]) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise RuntimeError("run tide prepare before review")
    runtime["review"] = {
        "approved": approved,
        "findings": findings,
        "created_at": now_iso(),
    }
    runtime["updated_at"] = now_iso()
    save_runtime(root, runtime)
    return runtime["review"]


def review_packet(root: Path) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise RuntimeError("run tide prepare before review")
    actual = changed_files(root)
    locks = matching_locks(root, actual or runtime.get("boundary", []))
    return {
        "task": runtime.get("task"),
        "boundary": runtime.get("boundary", []),
        "files": actual,
        "diff": current_diff(root, actual),
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
        "validations": runtime.get("validations", []),
        "review_focus": runtime.get("review_reasons", []),
        "instruction": "Read-only review. Return concise blocking and non-blocking findings.",
    }


def check(root: Path) -> dict[str, Any]:
    runtime = load_runtime(root)
    actual = changed_files(root)
    boundary = runtime.get("boundary", []) if runtime else []
    outside = sorted(path for path in actual if boundary and not _inside(path, boundary))
    locks = matching_locks(root, actual)
    validations = runtime.get("validations", []) if runtime else []
    passed_commands = {" ".join(item.get("command", [])) for item in validations if item.get("passed")}
    required = sorted({command for lock in locks for command in lock.validations})
    missing_required = [command for command in required if command not in passed_commands]
    failures = [item for item in validations if not item.get("passed")]
    review_required = bool(runtime and runtime.get("review_required")) or any(lock.review_required for lock in locks)
    review = runtime.get("review") if runtime else None
    hardgates = set(runtime.get("hardgates", [])) if runtime else set()
    authorized = set(runtime.get("authorized_hardgates", [])) if runtime else set()
    pending_hardgates = sorted(hardgates - authorized)

    blockers: list[str] = []
    if not runtime:
        blockers.append("no active Tide preparation")
    if actual and not boundary:
        blockers.append("no boundary declared")
    if outside:
        blockers.append("files changed outside the declared boundary")
    if pending_hardgates:
        blockers.append("hardgates not authorized")
    if actual and not validations:
        blockers.append("no validation recorded")
    if failures:
        blockers.append("one or more validations failed")
    if missing_required:
        blockers.append("Module Lock validations are missing")
    if review_required and not review:
        blockers.append("independent review required")
    if review and not review.get("approved"):
        blockers.append("independent review has blocking findings")

    ready = not blockers
    if runtime:
        runtime["status"] = "ready" if ready else "blocked"
        runtime["updated_at"] = now_iso()
        save_runtime(root, runtime)

    return {
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "files": actual,
        "boundary": boundary,
        "outside_boundary": outside,
        "locks": [lock.name for lock in locks],
        "required_validations": required,
        "missing_validations": missing_required,
        "validation_count": len(validations),
        "failed_validation_count": len(failures),
        "review_required": review_required,
        "review": review,
        "hardgates": sorted(hardgates),
        "authorized_hardgates": sorted(authorized),
        "pending_hardgates": pending_hardgates,
        "blockers": blockers,
    }


def _inside(path: str, boundary: list[str]) -> bool:
    from .locks import _matches

    return any(_matches(path, pattern) for pattern in boundary)
