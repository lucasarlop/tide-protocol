from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from .project import (
    TideError,
    changed_files,
    file_fingerprints,
    load_runtime,
    save_runtime,
)

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Any] = {}


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide guardrails are not installed")
    return _CORE


def install(core: ModuleType) -> None:
    global _CORE
    if getattr(core, "_additional_guardrails_installed", False):
        return
    _CORE = core
    for name in (
        "prepare",
        "revise",
        "preparation_report",
        "record_review",
        "submit_review",
        "check",
        "_outside_violations",
    ):
        _ORIGINALS[name] = getattr(core, name)

    core.prepare = prepare
    core.revise = revise
    core.preparation_report = preparation_report
    core.record_review = record_review
    core.submit_review = submit_review
    core.check = check
    core.external_acknowledge = external_acknowledge
    core._outside_violations = _outside_violations
    core._additional_guardrails_installed = True


def prepare(
    root: Path,
    task: str,
    files: list[str] | None = None,
    required_validations: list[str] | None = None,
) -> dict[str, Any]:
    _ORIGINALS["prepare"](root, task, files, required_validations)
    runtime = load_runtime(root)
    runtime.setdefault("acknowledged_external_changes", {})
    runtime.setdefault("scope_expansion_files", [])
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
    core = _core()
    before = load_runtime(root)
    if not before:
        raise TideError("run tide prepare before revise")

    old_boundary = list(before.get("boundary", []))
    requested_boundary = set(old_boundary)
    requested_boundary.update(add_files or [])
    requested_boundary.difference_update(remove_files or [])
    new_boundary = sorted(requested_boundary)
    changed = changed_files(root)

    newly_absorbed = {
        path
        for path in changed
        if not core._inside(path, old_boundary) and core._inside(path, new_boundary)
    }
    previous_scope = set(before.get("scope_expansion_files", []))
    scope_files = sorted(
        path
        for path in previous_scope | newly_absorbed
        if path in changed and core._inside(path, new_boundary)
    )
    previously_authorized = set(before.get("authorized_hardgates", []))
    acknowledgements = dict(before.get("acknowledged_external_changes", {}))

    _ORIGINALS["revise"](
        root,
        task=task,
        add_files=add_files,
        remove_files=remove_files,
        add_required_validations=add_required_validations,
        remove_required_validations=remove_required_validations,
    )
    runtime = load_runtime(root)
    hardgates = set(runtime.get("hardgates", []))
    authorized = set(runtime.get("authorized_hardgates", []))
    reasons = list(runtime.get("review_reasons", []))

    if scope_files:
        hardgates.add("scope_expansion")
        if "scope_expansion" in previously_authorized:
            authorized.add("scope_expansion")
        reasons.append(
            "changed files were added to the boundary after preparation; supervisor authorization required"
        )
    else:
        hardgates.discard("scope_expansion")
        authorized.discard("scope_expansion")

    runtime["scope_expansion_files"] = scope_files
    runtime["hardgates"] = sorted(hardgates)
    runtime["authorized_hardgates"] = sorted(authorized & hardgates)
    runtime["review_reasons"] = list(dict.fromkeys(reasons))
    runtime["acknowledged_external_changes"] = {
        path: value
        for path, value in acknowledgements.items()
        if not core._inside(path, new_boundary)
    }
    runtime["updated_at"] = core.now_iso()
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def external_acknowledge(
    root: Path,
    files: list[str],
    *,
    reason: str,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before acknowledging external changes")
    reason = reason.strip()
    if not reason:
        raise TideError("external acknowledgement requires a reason")

    candidates = sorted(dict.fromkeys(files))
    if not candidates:
        raise TideError("provide at least one external file")
    violations = set(_ORIGINALS["_outside_violations"](root, runtime))
    unknown = [path for path in candidates if path not in violations]
    if unknown:
        raise TideError(
            "files are not current outside-boundary violations: " + ", ".join(unknown)
        )

    fingerprints = file_fingerprints(root, candidates)
    acknowledgements = dict(runtime.get("acknowledged_external_changes", {}))
    timestamp = _core().now_iso()
    for path in candidates:
        acknowledgements[path] = {
            "fingerprint": fingerprints[path],
            "reason": reason,
            "acknowledged_at": timestamp,
        }
    runtime["acknowledged_external_changes"] = acknowledgements
    runtime["updated_at"] = timestamp
    save_runtime(root, runtime)
    return {
        "acknowledged": candidates,
        "reason": reason,
        "outside_boundary": _outside_violations(root, runtime),
    }


def _outside_violations(root: Path, runtime: dict[str, Any]) -> list[str]:
    violations = _ORIGINALS["_outside_violations"](root, runtime)
    acknowledgements = runtime.get("acknowledged_external_changes", {})
    if not isinstance(acknowledgements, dict):
        return violations

    remaining: list[str] = []
    for path in violations:
        value = acknowledgements.get(path)
        expected = value.get("fingerprint") if isinstance(value, dict) else None
        current = file_fingerprints(root, [path])[path]
        if not expected or expected != current:
            remaining.append(path)
    return sorted(remaining)


def preparation_report(
    root: Path,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime or load_runtime(root)
    report = _ORIGINALS["preparation_report"](root, runtime)
    acknowledged = runtime.get("acknowledged_external_changes", {})
    report["scope_expansion_files"] = list(runtime.get("scope_expansion_files", []))
    report["acknowledged_external_changes"] = [
        {
            "file": path,
            "reason": value.get("reason"),
            "acknowledged_at": value.get("acknowledged_at"),
        }
        for path, value in sorted(acknowledged.items())
        if isinstance(value, dict)
    ]
    return report


def _packet_truncated(root: Path, review_id: str | None) -> bool:
    if not review_id:
        return False
    from .artifacts import read_review_packet

    packet = read_review_packet(root, review_id)
    return bool((packet.get("diff") or {}).get("truncated", False))


def record_review(
    root: Path,
    *,
    approved: bool,
    findings: list[str],
    review_id: str | None = None,
) -> dict[str, Any]:
    truncated = _packet_truncated(root, review_id)
    if approved and truncated:
        raise TideError(
            "cannot approve a truncated review packet; reduce the task boundary or acknowledge unrelated external changes"
        )
    review = _ORIGINALS["record_review"](
        root,
        approved=approved,
        findings=findings,
        review_id=review_id,
    )
    if review_id:
        runtime = load_runtime(root)
        runtime["review"]["diff_truncated"] = truncated
        save_runtime(root, runtime)
        review = runtime["review"]
    return review


def submit_review(
    root: Path,
    *,
    review_id: str,
    submission_token: str,
    approved: bool,
    findings: list[str],
) -> dict[str, Any]:
    truncated = _packet_truncated(root, review_id)
    if approved and truncated:
        raise TideError(
            "cannot approve a truncated review packet; reduce the task boundary or acknowledge unrelated external changes"
        )
    _ORIGINALS["submit_review"](
        root,
        review_id=review_id,
        submission_token=submission_token,
        approved=approved,
        findings=findings,
    )
    runtime = load_runtime(root)
    runtime["review"]["diff_truncated"] = truncated
    save_runtime(root, runtime)
    return runtime["review"]


def check(root: Path) -> dict[str, Any]:
    report = _ORIGINALS["check"](root)
    runtime = load_runtime(root)
    review = runtime.get("review") if runtime else None
    blockers = list(report.get("blockers", []))
    if review and review.get("diff_truncated"):
        message = "independent review packet was truncated"
        if message not in blockers:
            blockers.append(message)

    ready = not blockers
    report["blockers"] = blockers
    report["ready"] = ready
    report["status"] = "ready" if ready else "blocked"
    report["scope_expansion_files"] = list(
        (runtime or {}).get("scope_expansion_files", [])
    )
    report["acknowledged_external_changes"] = preparation_report(
        root, runtime or {}
    ).get("acknowledged_external_changes", [])
    if runtime:
        runtime["status"] = report["status"]
        runtime["updated_at"] = _core().now_iso()
        save_runtime(root, runtime)
    return report
