from __future__ import annotations

import subprocess
import time
from pathlib import Path
from types import ModuleType
from typing import Any

from . import agility as _agility
from . import closure as _closure
from .project import TideError, diff_fingerprint, file_fingerprints, load_runtime, save_runtime

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Any] = {}


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide 1.0 controls are not installed")
    return _CORE


def install(core: ModuleType) -> None:
    global _CORE
    if getattr(core, "_v1_controls_installed", False):
        return
    _CORE = core
    for name in (
        "prepare",
        "revise",
        "split",
        "reopen",
        "preparation_report",
        "record_validation",
        "start_validation",
        "validation_status",
        "create_review_packet",
        "submit_review",
        "record_review",
        "check",
        "handoff",
        "_outside_violations",
    ):
        _ORIGINALS[name] = getattr(core, name)

    core.prepare = prepare
    core.revise = revise
    core.split = split
    core.reopen = reopen
    core.preparation_report = preparation_report
    core.record_validation = record_validation
    core.start_validation = start_validation
    core.validation_status = validation_status
    core.validation_wait = validation_wait
    core.create_review_packet = create_review_packet
    core.submit_review = submit_review
    core.record_review = record_review
    core.check = check
    core.handoff = handoff
    core.resume = resume
    core.operational_verify = operational_verify
    core._outside_violations = _outside_violations
    core._v1_controls_installed = True


def _ensure_v1(runtime: dict[str, Any]) -> None:
    _closure._ensure_defaults(runtime)
    runtime.setdefault("protocol_version", "1.0")
    runtime.setdefault("autonomy", "trusted")
    runtime.setdefault("lifecycle", "active")
    runtime.setdefault("segment_receipts", [])
    runtime.setdefault("operational_checks", [])
    runtime.setdefault("approved_fingerprint", None)
    runtime.setdefault("approved_files", {})
    runtime.setdefault("approved_at", None)
    runtime.setdefault("committed_sha", None)
    runtime.setdefault("resume_checkpoint", None)


def _task_files(root: Path, runtime: dict[str, Any]) -> list[str]:
    return list(_core()._task_files(root, runtime))


def _current_fingerprint(root: Path, runtime: dict[str, Any]) -> str:
    return diff_fingerprint(root, _task_files(root, runtime))


def _checkpoint(root: Path, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = runtime or load_runtime(root)
    if not runtime:
        return {"active": False, "next_action": "prepare a bounded task"}
    _ensure_v1(runtime)
    review = runtime.get("review") if isinstance(runtime.get("review"), dict) else {}
    blockers = [
        {
            "id": str(item.get("id") or "finding"),
            "message": str(item.get("message") or ""),
            "paths": list(item.get("paths") or []),
            "expected_action": str(item.get("expected_action") or ""),
        }
        for item in review.get("findings", [])
        if isinstance(item, dict) and item.get("severity") == "blocking"
    ]
    pending = sorted(set(runtime.get("hardgates", [])) - set(runtime.get("authorized_hardgates", [])))
    checkpoint = {
        "active": True,
        "protocol_version": "1.0",
        "task": runtime.get("task"),
        "segment": int(runtime.get("segment_index", 0)),
        "segment_id": runtime.get("segment_id"),
        "lifecycle": runtime.get("lifecycle"),
        "boundary": list(runtime.get("boundary", [])),
        "changed_files": _task_files(root, runtime),
        "validation_count": len(runtime.get("validations", [])),
        "review": {
            "review_id": review.get("review_id"),
            "approved": bool(review.get("approved")),
            "blocking": blockers,
        },
        "follow_ups": list(runtime.get("follow_up_tasks", [])),
        "pending_hardgates": pending,
        "split_required": bool(runtime.get("split_required")),
        "next_action": _next_action(runtime, blockers, pending),
        "start_new_session": bool(
            int(runtime.get("workflow_metrics", {}).get("review_attempts", 0)) >= 3
            or int(runtime.get("segment_index", 0)) >= 2
        ),
    }
    runtime["resume_checkpoint"] = checkpoint
    runtime["updated_at"] = _closure._now_iso()
    save_runtime(root, runtime)
    return checkpoint


def _next_action(runtime: dict[str, Any], blockers: list[dict[str, Any]], pending: list[str]) -> str:
    if pending:
        return "ask one concise decision question for the pending gate"
    if blockers:
        return "fix only the listed blocking finding, then run targeted validation"
    if runtime.get("split_required"):
        return "split into a smaller child segment"
    if runtime.get("lifecycle") == "operational_verification":
        return "run operational checks without reopening code review"
    if runtime.get("lifecycle") in {"approved", "committed", "closed"}:
        return "closure ready"
    return "implement the smallest safe delta"


def _save_and_report(root: Path, runtime: dict[str, Any]) -> dict[str, Any]:
    save_runtime(root, runtime)
    report = _ORIGINALS["preparation_report"](root, runtime)
    report["lifecycle"] = runtime.get("lifecycle")
    report["autonomy"] = runtime.get("autonomy")
    report["segment_receipt_count"] = len(runtime.get("segment_receipts", []))
    report["resume"] = _checkpoint(root, runtime)
    return report


def prepare(root: Path, task: str, files: list[str] | None = None, required_validations: list[str] | None = None) -> dict[str, Any]:
    _ORIGINALS["prepare"](root, task, files, required_validations)
    runtime = load_runtime(root)
    _ensure_v1(runtime)
    runtime["lifecycle"] = "active"
    runtime["segment_receipts"] = []
    runtime["operational_checks"] = []
    return _save_and_report(root, runtime)


def revise(root: Path, **kwargs: Any) -> dict[str, Any]:
    result = _ORIGINALS["revise"](root, **kwargs)
    runtime = load_runtime(root)
    _ensure_v1(runtime)
    runtime["lifecycle"] = "active"
    _checkpoint(root, runtime)
    return {**result, "lifecycle": runtime["lifecycle"]}


def _receipt(root: Path, runtime: dict[str, Any]) -> dict[str, Any] | None:
    review = runtime.get("review") if isinstance(runtime.get("review"), dict) else None
    if not review or not review.get("approved"):
        return None
    files = _task_files(root, runtime)
    return {
        "segment_id": runtime.get("segment_id"),
        "segment_index": runtime.get("segment_index"),
        "task": runtime.get("task"),
        "boundary": list(runtime.get("boundary", [])),
        "files": file_fingerprints(root, files),
        "review_id": review.get("review_id"),
        "approved_at": review.get("created_at") or _closure._now_iso(),
    }


def split(root: Path, *, task: str, files: list[str]) -> dict[str, Any]:
    before = load_runtime(root)
    if not before:
        raise TideError("run tide prepare before splitting")
    _ensure_v1(before)
    receipts = list(before.get("segment_receipts", []))
    receipt = _receipt(root, before)
    if receipt:
        receipts.append(receipt)
    result = _ORIGINALS["split"](root, task=task, files=files)
    runtime = load_runtime(root)
    _ensure_v1(runtime)
    runtime["segment_receipts"] = receipts
    runtime["lifecycle"] = "active"
    _checkpoint(root, runtime)
    save_runtime(root, runtime)
    return {**result, "segment_receipt_count": len(receipts), "lifecycle": "active"}


def reopen(root: Path, *, reason: str) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before reopen")
    _ensure_v1(runtime)
    approved = runtime.get("approved_fingerprint")
    current = _current_fingerprint(root, runtime)
    if approved and approved == current:
        runtime["lifecycle"] = "operational_verification"
        runtime["closure_locked"] = True
        runtime["closure_reason"] = reason.strip()
        return _save_and_report(root, runtime)

    _ORIGINALS["reopen"](root, reason=reason)
    runtime = load_runtime(root)
    _ensure_v1(runtime)
    # Trusted autonomy: a concrete defect may reopen automatically.
    hardgates = set(runtime.get("hardgates", []))
    authorized = set(runtime.get("authorized_hardgates", []))
    if "closure_reopen" in hardgates:
        authorized.add("closure_reopen")
    runtime["authorized_hardgates"] = sorted(authorized & hardgates)
    runtime["lifecycle"] = "active"
    return _save_and_report(root, runtime)


def _find_reusable_final(root: Path, runtime: dict[str, Any], command: list[str], covers: list[str]) -> dict[str, Any] | None:
    for item in reversed(runtime.get("validations", [])):
        if item.get("phase") != "final":
            continue
        if list(item.get("command") or []) != list(command):
            continue
        if covers and sorted(item.get("covers") or []) != sorted(covers):
            continue
        if item.get("passed") and _agility._validation_is_current(root, item):
            return {**item, "reused": True}
    return None


def record_validation(root: Path, command: list[str], timeout: int = 300, *, covers: list[str] | None = None, phase: str = "targeted") -> dict[str, Any]:
    runtime = load_runtime(root)
    if runtime and phase == "final":
        reusable = _find_reusable_final(root, runtime, command, list(covers or []))
        if reusable:
            return reusable
    result = _ORIGINALS["record_validation"](root, command, timeout, covers=covers, phase=phase)
    runtime = load_runtime(root)
    if runtime:
        _ensure_v1(runtime)
        _checkpoint(root, runtime)
    return result


def start_validation(root: Path, command: list[str], timeout: int = 300, *, covers: list[str] | None = None, phase: str = "targeted") -> dict[str, Any]:
    runtime = load_runtime(root)
    if runtime and phase == "final":
        reusable = _find_reusable_final(root, runtime, command, list(covers or []))
        if reusable:
            return reusable
    return _ORIGINALS["start_validation"](root, command, timeout, covers=covers, phase=phase)


def validation_status(root: Path, validation_id: str) -> dict[str, Any]:
    result = _ORIGINALS["validation_status"](root, validation_id)
    if result.get("status") in {"starting", "running"}:
        result["passed"] = None
    return result


def validation_wait(root: Path, validation_id: str, wait_seconds: int = 20) -> dict[str, Any]:
    deadline = time.monotonic() + max(1, min(int(wait_seconds), 60))
    while True:
        result = validation_status(root, validation_id)
        if result.get("status") == "completed":
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {**result, "passed": None, "poll_after_seconds": min(30, max(5, int(wait_seconds)))}
        time.sleep(min(1.0, remaining))


def create_review_packet(root: Path, *, full: bool = False, full_reason: str | None = None) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before review")
    _ensure_v1(runtime)
    current = _current_fingerprint(root, runtime)
    if runtime.get("approved_fingerprint") == current:
        raise TideError("current fingerprint is already approved; no additional review is allowed")
    result = _ORIGINALS["create_review_packet"](root, full=full, full_reason=full_reason)
    runtime = load_runtime(root)
    if runtime:
        runtime["lifecycle"] = "reviewing"
        _checkpoint(root, runtime)
    return result


def _enrich_findings(findings: list[Any]) -> list[Any]:
    enriched: list[Any] = []
    for item in findings:
        if not isinstance(item, dict):
            enriched.append(item)
            continue
        value = dict(item)
        value.setdefault("paths", [])
        value.setdefault("expected_action", "")
        enriched.append(value)
    return enriched


def _approval_metadata(root: Path, review: dict[str, Any]) -> dict[str, Any]:
    runtime = load_runtime(root)
    _ensure_v1(runtime)
    review["findings"] = _enrich_findings(list(review.get("findings") or []))
    runtime["review"] = review
    if review.get("approved"):
        files = _task_files(root, runtime)
        runtime["approved_fingerprint"] = diff_fingerprint(root, files)
        runtime["approved_files"] = file_fingerprints(root, files)
        runtime["approved_at"] = _closure._now_iso()
        runtime["lifecycle"] = "approved"
    else:
        runtime["lifecycle"] = "active"
    _checkpoint(root, runtime)
    save_runtime(root, runtime)
    return review


def submit_review(root: Path, **kwargs: Any) -> dict[str, Any]:
    kwargs["findings"] = _enrich_findings(list(kwargs.get("findings") or []))
    review = _ORIGINALS["submit_review"](root, **kwargs)
    return _approval_metadata(root, review)


def record_review(root: Path, **kwargs: Any) -> dict[str, Any]:
    kwargs["findings"] = _enrich_findings(list(kwargs.get("findings") or []))
    review = _ORIGINALS["record_review"](root, **kwargs)
    return _approval_metadata(root, review)


def operational_verify(root: Path, *, name: str, passed: bool, details: str = "") -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before operational verification")
    _ensure_v1(runtime)
    record = {
        "name": name.strip(),
        "passed": bool(passed),
        "details": details.strip()[:1000],
        "recorded_at": _closure._now_iso(),
    }
    runtime["operational_checks"].append(record)
    runtime["lifecycle"] = "operational_verification"
    _checkpoint(root, runtime)
    save_runtime(root, runtime)
    return record


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _approved_tree_current(root: Path, runtime: dict[str, Any]) -> bool:
    expected = runtime.get("approved_files")
    if not isinstance(expected, dict) or not expected:
        return False
    current = file_fingerprints(root, list(expected))
    return current == expected


def check(root: Path) -> dict[str, Any]:
    runtime = load_runtime(root)
    if runtime:
        _ensure_v1(runtime)
        if runtime.get("approved_fingerprint") and _approved_tree_current(root, runtime):
            if not _git(root, "status", "--porcelain", "--", *runtime.get("approved_files", {}).keys()):
                runtime["committed_sha"] = _git(root, "rev-parse", "HEAD") or None
                runtime["lifecycle"] = "committed" if runtime["committed_sha"] else "approved"
                runtime["closure_locked"] = True
                save_runtime(root, runtime)
    report = _ORIGINALS["check"](root)
    runtime = load_runtime(root)
    if runtime:
        _ensure_v1(runtime)
        report["lifecycle"] = runtime.get("lifecycle")
        report["committed_sha"] = runtime.get("committed_sha")
        report["segment_receipt_count"] = len(runtime.get("segment_receipts", []))
        report["resume"] = _checkpoint(root, runtime)
    return report


def _outside_violations(root: Path, runtime: dict[str, Any]) -> list[str]:
    violations = list(_ORIGINALS["_outside_violations"](root, runtime))
    receipts = runtime.get("segment_receipts", [])
    covered: dict[str, str] = {}
    for receipt in receipts:
        if isinstance(receipt, dict) and isinstance(receipt.get("files"), dict):
            covered.update({str(path): str(value) for path, value in receipt["files"].items()})
    remaining = []
    for path in violations:
        expected = covered.get(path)
        current = file_fingerprints(root, [path]).get(path)
        if not expected or expected != current:
            remaining.append(path)
    return sorted(remaining)


def handoff(root: Path) -> dict[str, Any]:
    return _checkpoint(root)


def resume(root: Path) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        return {"active": False, "next_action": "prepare a bounded task"}
    checkpoint = runtime.get("resume_checkpoint")
    if isinstance(checkpoint, dict):
        return _checkpoint(root, runtime)
    return _checkpoint(root, runtime)


def preparation_report(root: Path, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = runtime or load_runtime(root)
    report = _ORIGINALS["preparation_report"](root, runtime)
    if runtime:
        _ensure_v1(runtime)
        report["lifecycle"] = runtime.get("lifecycle")
        report["autonomy"] = runtime.get("autonomy")
        report["segment_receipt_count"] = len(runtime.get("segment_receipts", []))
        report["resume"] = _checkpoint(root, runtime)
    return report
