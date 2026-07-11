from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
from typing import Any

from .artifacts import (
    consume_review_submission,
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
    run_git,
    save_runtime,
)
from .validation_jobs import compact_job, read_job, refresh_job, save_job, start_job


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _normalize_required_validations(values: list[str] | None) -> list[str]:
    return sorted(
        dict.fromkeys(
            value.strip()
            for value in (values or [])
            if isinstance(value, str) and value.strip()
        )
    )


def prepare(
    root: Path,
    task: str,
    files: list[str] | None = None,
    required_validations: list[str] | None = None,
) -> dict[str, Any]:
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
        "version": 3,
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
        "required_validations": _normalize_required_validations(required_validations),
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
    add_required_validations: list[str] | None = None,
    remove_required_validations: list[str] | None = None,
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

    required = set(_normalize_required_validations(runtime.get("required_validations", [])))
    required.update(_normalize_required_validations(add_required_validations))
    required.difference_update(_normalize_required_validations(remove_required_validations))

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
            "required_validations": sorted(required),
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


def _required_validations(runtime: dict[str, Any], locks: list[Any]) -> list[str]:
    task_required = _normalize_required_validations(runtime.get("required_validations", []))
    lock_required = [command for lock in locks for command in lock.validations]
    return sorted(dict.fromkeys([*task_required, *lock_required]))


def preparation_report(
    root: Path,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime or load_runtime(root)
    boundary = runtime.get("boundary", [])
    locks = matching_locks(root, boundary)
    required_validations = _required_validations(runtime, locks)
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
        "task_required_validations": _normalize_required_validations(
            runtime.get("required_validations", [])
        ),
        "required_validations": required_validations,
        "rules": {
            "writers": 1,
            "reviewers": 1 if runtime.get("review_required") else 0,
            "commit_requires_supervisor": True,
        },
    }


def _record_validation_result(
    root: Path,
    runtime: dict[str, Any],
    result: dict[str, Any],
    *,
    files: list[str],
    fingerprint: str,
    validation_id: str | None = None,
) -> dict[str, Any]:
    if validation_id:
        for existing in runtime.get("validations", []):
            if existing.get("validation_id") == validation_id:
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
        "diff_fingerprint": fingerprint,
    }
    if validation_id:
        evidence["validation_id"] = validation_id
    runtime.setdefault("validations", []).append(evidence)
    runtime["updated_at"] = now_iso()
    save_runtime(root, runtime)
    return evidence


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
    return _record_validation_result(
        root,
        runtime,
        result,
        files=task_files,
        fingerprint=diff_fingerprint(root, task_files),
    )


def start_validation(
    root: Path,
    command: list[str],
    timeout: int = 300,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before validation")
    if not command:
        raise TideError("validation command cannot be empty")
    task_files = _task_files(root, runtime)
    return start_job(
        root,
        command=command,
        timeout=timeout,
        files=task_files,
        diff_fingerprint=diff_fingerprint(root, task_files),
        revision=int(runtime.get("revision", 0)),
        created_at=now_iso(),
    )


def validation_status(root: Path, validation_id: str) -> dict[str, Any]:
    job = refresh_job(root, validation_id)
    if job.get("status") == "completed" and not job.get("recorded"):
        result = job.get("result")
        if not isinstance(result, dict):
            raise TideError("completed validation job has no result")
        runtime = load_runtime(root)
        if not runtime:
            raise TideError("run tide prepare before collecting validation")
        evidence = _record_validation_result(
            root,
            runtime,
            result,
            files=list(job.get("files") or []),
            fingerprint=str(job.get("diff_fingerprint") or ""),
            validation_id=validation_id,
        )
        job["recorded"] = True
        job["evidence"] = evidence
        save_job(root, job)
    return compact_job(read_job(root, validation_id))


def validation_log(root: Path, log_id: str) -> dict[str, Any]:
    return read_validation_log(root, log_id)


def _review_value(
    *,
    approved: bool,
    findings: list[str],
    review_id: str | None,
    task_files: list[str],
    fingerprint: str,
    receipt_id: str | None = None,
) -> dict[str, Any]:
    value = {
        "approved": approved,
        "findings": findings,
        "review_id": review_id,
        "created_at": now_iso(),
        "files": task_files,
        "diff_fingerprint": fingerprint,
    }
    if receipt_id:
        value["receipt_id"] = receipt_id
    return value


def record_review(
    root: Path,
    *,
    approved: bool,
    findings: list[str],
    review_id: str | None = None,
) -> dict[str, Any]:
    """Legacy/manual review recording used by the CLI.

    Agent reviewers should use submit_review so the verdict is bound to the
    packet's one-time submission token.
    """
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before review")
    task_files = _task_files(root, runtime)
    fingerprint = diff_fingerprint(root, task_files)
    if review_id:
        packet = read_review_packet(root, review_id)
        if packet.get("diff_fingerprint") != fingerprint:
            raise TideError("review packet is stale for the current diff")
    runtime["review"] = _review_value(
        approved=approved,
        findings=findings,
        review_id=review_id,
        task_files=task_files,
        fingerprint=fingerprint,
    )
    runtime["updated_at"] = now_iso()
    save_runtime(root, runtime)
    return runtime["review"]


def submit_review(
    root: Path,
    *,
    review_id: str,
    submission_token: str,
    approved: bool,
    findings: list[str],
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before review")
    task_files = _task_files(root, runtime)
    fingerprint = diff_fingerprint(root, task_files)
    packet = read_review_packet(root, review_id)
    if packet.get("diff_fingerprint") != fingerprint:
        raise TideError("review packet is stale for the current diff")
    provisional = _review_value(
        approved=approved,
        findings=findings,
        review_id=review_id,
        task_files=task_files,
        fingerprint=fingerprint,
    )
    receipt = consume_review_submission(
        root,
        review_id,
        submission_token,
        provisional,
    )
    runtime["review"] = {**provisional, "receipt_id": receipt["receipt_id"]}
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
    passed_commands = {
        " ".join(item.get("command", []))
        for item in current_validations
        if item.get("passed")
    }
    required = _required_validations(runtime, locks)
    missing_required = [command for command in required if command not in passed_commands]
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
        "required_validations": required,
        "missing_validations": missing_required,
        "stale_validation_count": len(runtime.get("validations", [])) - len(current_validations),
        "review_focus": focus,
        "instruction": (
            "Read-only review. Check behavior, stability, tests, security, boundary compliance, "
            "and simplicity only when signaled. Submit the verdict directly with review_submit "
            "using this packet's review_id and submission_token. Do not ask the writer to relay it."
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
    required = _required_validations(runtime or {}, locks)
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
        blockers.append("required validations are missing for the current diff")
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
        "task_required_validations": _normalize_required_validations(
            (runtime or {}).get("required_validations", [])
        ),
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


class _FunctionSizeVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.sizes: dict[str, int] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        key = ".".join([*self.stack, node.name])
        if getattr(node, "end_lineno", None):
            self.sizes[key] = int(node.end_lineno) - int(node.lineno) + 1
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._visit_function(node)


def _python_function_sizes(text: str) -> dict[str, int]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    visitor = _FunctionSizeVisitor()
    visitor.visit(tree)
    return visitor.sizes


def _head_text(root: Path, raw: str) -> str | None:
    result = run_git(["show", f"HEAD:{raw}"], cwd=root, check=False)
    return result.stdout if result.returncode == 0 else None


def _simplicity_signals(root: Path, files: list[str]) -> list[str]:
    signals: list[str] = []
    for raw in files:
        path = root / raw
        if not path.is_file() or path.suffix.lower() not in {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".java",
            ".go",
            ".rs",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.count("\n") + 1
        tracked = is_tracked_in_head(root, raw)
        if not tracked and lines > 400:
            signals.append(f"simplicity: new file {raw} has {lines} lines")
        if path.suffix.lower() != ".py":
            continue

        current_sizes = _python_function_sizes(text)
        baseline_sizes = _python_function_sizes(_head_text(root, raw) or "") if tracked else {}
        for name, size in current_sizes.items():
            previous = baseline_sizes.get(name)
            if previous is None and size > 100:
                signals.append(
                    f"simplicity: new function {name} in {raw} has {size} lines"
                )
            elif previous is not None and size > 100 and size - previous > 40:
                signals.append(
                    f"simplicity: function {name} in {raw} grew by {size - previous} lines to {size}"
                )
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
