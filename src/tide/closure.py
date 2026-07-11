from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

from . import agility as _agility
from . import artifacts as _artifacts
from .project import (
    TideError,
    diff_fingerprint,
    file_fingerprints,
    load_runtime,
    save_runtime,
)

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Any] = {}
_ORIGINAL_BUDGET_STATE = _agility._budget_state
_ORIGINAL_ELAPSED_MINUTES = _agility._elapsed_minutes
_ORIGINAL_LATEST_REVIEW = _agility._latest_review
_ORIGINAL_NORMALIZE_FINDINGS = _agility._normalize_findings
_ORIGINAL_LIST_REVIEW_RESOURCES = _artifacts.list_review_resources

_FULL_REVIEW_TERMS = {
    "architecture",
    "arquitetura",
    "invariant",
    "invariante",
    "contract",
    "contrato",
    "schema",
    "esquema",
    "security",
    "segurança",
    "boundary",
    "fronteira",
}


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide closure controls are not installed")
    return _CORE


def _now() -> datetime:
    return datetime.now().astimezone()


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _boundary_signature(boundary: list[str]) -> str:
    payload = "\n".join(sorted(str(item) for item in boundary))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _segment_id() -> str:
    return f"segment-{uuid.uuid4().hex[:12]}"


def _metrics(runtime: dict[str, Any]) -> dict[str, int]:
    metrics = runtime.setdefault("workflow_metrics", {})
    for key in (
        "review_cycles",
        "review_attempts",
        "review_cancelled",
        "review_packets",
        "scope_expansions",
        "validation_runs",
        "reopens",
    ):
        metrics[key] = int(metrics.get(key, 0))
    return metrics


def _ensure_defaults(runtime: dict[str, Any]) -> None:
    runtime.setdefault("segment_id", _segment_id())
    runtime.setdefault("segment_index", 0)
    runtime.setdefault("parent_segment_id", None)
    runtime.setdefault("segment_started_at", runtime.get("created_at") or _now_iso())
    runtime.setdefault("segment_history", [])
    runtime.setdefault("boundary_signature", _boundary_signature(list(runtime.get("boundary", []))))
    runtime.setdefault("pending_review", None)
    runtime.setdefault("extended_investigation_grant", None)
    runtime.setdefault("follow_up_records", [])
    _metrics(runtime)


def install(core: ModuleType) -> None:
    global _CORE
    if getattr(core, "_closure_controls_installed", False):
        return
    _CORE = core
    for name in (
        "prepare",
        "revise",
        "reopen",
        "authorize",
        "preparation_report",
        "review_packet",
        "create_review_packet",
        "get_review_packet",
        "record_review",
        "submit_review",
        "check",
    ):
        _ORIGINALS[name] = getattr(core, name)

    core.prepare = prepare
    core.revise = revise
    core.split = split
    core.reopen = reopen
    core.authorize = authorize
    core.preparation_report = preparation_report
    core.review_packet = review_packet
    core.create_review_packet = create_review_packet
    core.get_review_packet = get_review_packet
    core.record_review = record_review
    core.submit_review = submit_review
    core.check = check
    core.handoff = handoff
    core._closure_controls_installed = True

    _agility._budget_state = _budget_state
    _agility._elapsed_minutes = _elapsed_minutes
    _agility._latest_review = _latest_review
    _agility._normalize_findings = _normalize_findings
    _artifacts.list_review_resources = list_review_resources


def _elapsed_minutes(runtime: dict[str, Any]) -> int:
    raw = runtime.get("segment_started_at") or runtime.get("created_at")
    if not isinstance(raw, str):
        return 0
    try:
        started = datetime.fromisoformat(raw)
        if started.tzinfo is None:
            started = started.astimezone()
        return max(0, int((_now() - started).total_seconds() // 60))
    except ValueError:
        return _ORIGINAL_ELAPSED_MINUTES(runtime)


def _budget_state(runtime: dict[str, Any]) -> dict[str, Any]:
    _ensure_defaults(runtime)
    state = _ORIGINAL_BUDGET_STATE(runtime)
    metrics = _metrics(runtime)
    max_attempts = int(state["budget"].get("max_review_cycles", 2)) + 2
    reasons = list(state.get("split_reasons", []))
    if metrics["review_attempts"] > max_attempts:
        reasons.append("review attempt budget exceeded")
    state["budget"]["max_review_attempts"] = max_attempts
    state["metrics"] = {**state.get("metrics", {}), **metrics}
    state["split_reasons"] = list(dict.fromkeys(reasons))
    state["split_required"] = bool(state["split_reasons"])
    if metrics["review_attempts"] == max_attempts:
        warning = "review attempt budget is at its limit"
        current = str(state.get("closure_warning") or "").strip()
        state["closure_warning"] = "; ".join(item for item in (current, warning) if item)
    return state


def _latest_review(runtime: dict[str, Any]) -> dict[str, Any] | None:
    _ensure_defaults(runtime)
    segment_id = runtime.get("segment_id")
    boundary_signature = runtime.get("boundary_signature")
    candidates = [
        item
        for item in [*runtime.get("review_history", []), runtime.get("review")]
        if isinstance(item, dict) and item.get("review_id")
    ]
    compatible = [
        item
        for item in candidates
        if item.get("segment_id") == segment_id
        and item.get("boundary_signature") == boundary_signature
    ]
    if compatible:
        return compatible[-1]
    if int(runtime.get("segment_index", 0)) == 0:
        legacy = [item for item in candidates if not item.get("segment_id")]
        if legacy:
            return legacy[-1]
    return None


def _finding_id(message: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", message.lower()).strip("-")
    if normalized:
        return normalized[:72]
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


def _normalize_findings(findings: list[Any], *, approved: bool) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in findings:
        base = _ORIGINAL_NORMALIZE_FINDINGS([item], approved=approved)
        if not base:
            continue
        value = dict(base[0])
        supplied_id = str(item.get("id") or "").strip() if isinstance(item, dict) else ""
        value["id"] = supplied_id or _finding_id(value["message"])
        normalized.append(value)
    return normalized


def _apply_segment_metadata(runtime: dict[str, Any], review: dict[str, Any]) -> None:
    review["segment_id"] = runtime.get("segment_id")
    review["boundary_signature"] = runtime.get("boundary_signature")
    for item in runtime.get("review_history", []):
        if isinstance(item, dict) and item.get("review_id") == review.get("review_id"):
            item.update(review)


def _dedupe_followups(runtime: dict[str, Any]) -> None:
    records: dict[str, dict[str, str]] = {}
    for record in runtime.get("follow_up_records", []):
        if isinstance(record, dict) and record.get("id"):
            records[str(record["id"])] = {
                "id": str(record["id"]),
                "message": str(record.get("message") or ""),
            }
    for review in [*runtime.get("review_history", []), runtime.get("review")]:
        if not isinstance(review, dict):
            continue
        for finding in review.get("findings", []):
            if not isinstance(finding, dict) or finding.get("severity") != "follow_up":
                continue
            finding_id = str(finding.get("id") or _finding_id(str(finding.get("message") or "")))
            records[finding_id] = {
                "id": finding_id,
                "message": str(finding.get("message") or ""),
            }
    runtime["follow_up_records"] = list(records.values())
    runtime["follow_up_tasks"] = [item["message"] for item in records.values() if item["message"]]


def prepare(
    root: Path,
    task: str,
    files: list[str] | None = None,
    required_validations: list[str] | None = None,
) -> dict[str, Any]:
    _ORIGINALS["prepare"](root, task, files, required_validations)
    runtime = load_runtime(root)
    runtime["segment_id"] = _segment_id()
    runtime["segment_index"] = 0
    runtime["parent_segment_id"] = None
    runtime["segment_started_at"] = _now_iso()
    runtime["segment_history"] = []
    runtime["boundary_signature"] = _boundary_signature(list(runtime.get("boundary", [])))
    runtime["pending_review"] = None
    runtime["extended_investigation_grant"] = None
    runtime["follow_up_records"] = []
    _metrics(runtime).update(
        {
            "review_cycles": 0,
            "review_attempts": 0,
            "review_cancelled": 0,
            "review_packets": 0,
            "scope_expansions": 0,
            "validation_runs": 0,
            "reopens": 0,
        }
    )
    _agility._apply_budget(runtime)
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
    runtime["boundary_signature"] = _boundary_signature(list(runtime.get("boundary", [])))
    runtime["pending_review"] = None
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def _archive_segment(runtime: dict[str, Any]) -> dict[str, Any]:
    return {
        "segment_id": runtime.get("segment_id"),
        "segment_index": runtime.get("segment_index"),
        "task": runtime.get("task"),
        "boundary": list(runtime.get("boundary", [])),
        "boundary_signature": runtime.get("boundary_signature"),
        "started_at": runtime.get("segment_started_at"),
        "ended_at": _now_iso(),
        "status": runtime.get("status"),
        "workflow_metrics": dict(_metrics(runtime)),
        "review": runtime.get("review"),
        "follow_up_tasks": list(runtime.get("follow_up_tasks", [])),
    }


def split(root: Path, *, task: str, files: list[str]) -> dict[str, Any]:
    before = load_runtime(root)
    if not before:
        raise TideError("run tide prepare before splitting")
    _ensure_defaults(before)
    task = task.strip()
    target = sorted(dict.fromkeys(str(item).strip() for item in files if str(item).strip()))
    if not task:
        raise TideError("split requires a concrete child task")
    if not target:
        raise TideError("split requires a non-empty child boundary")

    current_files = _core()._task_files(root, before)
    selected = [path for path in current_files if _core()._inside(path, target)]
    if not selected:
        raise TideError("split boundary does not contain any changed file from the current segment")

    history = list(before.get("segment_history", []))
    history.append(_archive_segment(before))
    previous_segment_id = str(before.get("segment_id"))
    previous_validations = list(before.get("validations", []))
    previous_followups = list(before.get("follow_up_tasks", []))
    previous_records = list(before.get("follow_up_records", []))
    old_boundary = list(before.get("boundary", []))

    before["closure_locked"] = False
    before["review"] = None
    save_runtime(root, before)
    _ORIGINALS["revise"](
        root,
        task=task,
        add_files=target,
        remove_files=old_boundary,
        add_required_validations=None,
        remove_required_validations=None,
    )
    runtime = load_runtime(root)
    _ensure_defaults(runtime)
    compatible_validations = []
    for item in previous_validations:
        evidence_files = [str(path) for path in item.get("files", [])]
        if evidence_files and all(_core()._inside(path, target) for path in evidence_files):
            if _agility._validation_is_current(root, item):
                compatible_validations.append(item)

    runtime["segment_history"] = history
    runtime["parent_segment_id"] = previous_segment_id
    runtime["segment_id"] = _segment_id()
    runtime["segment_index"] = int(before.get("segment_index", 0)) + 1
    runtime["segment_started_at"] = _now_iso()
    runtime["boundary_signature"] = _boundary_signature(list(runtime.get("boundary", [])))
    runtime["workflow_metrics"] = {
        "review_cycles": 0,
        "review_attempts": 0,
        "review_cancelled": 0,
        "review_packets": 0,
        "scope_expansions": 0,
        "validation_runs": 0,
        "reopens": 0,
    }
    runtime["review"] = None
    runtime["review_history"] = []
    runtime["pending_review"] = None
    runtime["validations"] = compatible_validations
    runtime["follow_up_tasks"] = previous_followups
    runtime["follow_up_records"] = previous_records
    runtime["closure_locked"] = False
    runtime["closure_reason"] = None
    runtime["split_required"] = False
    runtime["split_reasons"] = []
    runtime["closure_warning"] = None
    runtime["extended_investigation_grant"] = None
    hardgates = set(runtime.get("hardgates", [])) - {"extended_investigation", "closure_reopen"}
    authorized = set(runtime.get("authorized_hardgates", [])) - {"extended_investigation", "closure_reopen"}
    runtime["hardgates"] = sorted(hardgates)
    runtime["authorized_hardgates"] = sorted(authorized & hardgates)
    runtime["status"] = "revising"
    _agility._apply_budget(runtime)
    runtime["updated_at"] = _now_iso()
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def reopen(root: Path, *, reason: str) -> dict[str, Any]:
    result = _ORIGINALS["reopen"](root, reason=reason)
    runtime = load_runtime(root)
    _ensure_defaults(runtime)
    runtime["pending_review"] = None
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def authorize(
    root: Path,
    gates: list[str] | None = None,
    *,
    all_gates: bool = False,
) -> dict[str, Any]:
    result = _ORIGINALS["authorize"](root, gates, all_gates=all_gates)
    runtime = load_runtime(root)
    _ensure_defaults(runtime)
    requested = set(runtime.get("hardgates", [])) if all_gates else set(gates or [])
    if "extended_investigation" in requested:
        runtime["extended_investigation_grant"] = {
            "granted_at": _now_iso(),
            "expires_at": (_now() + timedelta(minutes=30)).isoformat(timespec="seconds"),
            "remaining_review_packets": 2,
        }
    save_runtime(root, runtime)
    return preparation_report(root, runtime)


def _grant_available(runtime: dict[str, Any]) -> bool:
    grant = runtime.get("extended_investigation_grant")
    if not isinstance(grant, dict):
        return False
    try:
        expires = datetime.fromisoformat(str(grant.get("expires_at") or ""))
    except ValueError:
        return False
    return expires >= _now() and int(grant.get("remaining_review_packets", 0)) > 0


def _full_review_allowed(runtime: dict[str, Any], reason: str | None) -> None:
    previous = _latest_review(runtime)
    if not previous:
        return
    reason = str(reason or "").strip()
    if not reason:
        raise TideError("full review after the baseline requires full_reason")
    lowered = reason.lower()
    if not any(term in lowered for term in _FULL_REVIEW_TERMS):
        raise TideError("full_reason must identify an architecture, invariant, contract, schema, security, or boundary change")


def review_packet(
    root: Path,
    *,
    full: bool = False,
    full_reason: str | None = None,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before review")
    _ensure_defaults(runtime)
    if full:
        _full_review_allowed(runtime, full_reason)
    packet = _ORIGINALS["review_packet"](root, full=full)
    packet["segment_id"] = runtime.get("segment_id")
    packet["boundary_signature"] = runtime.get("boundary_signature")
    packet["full_reason"] = str(full_reason or "").strip() or None
    return packet


def _packet_summary(packet: dict[str, Any], *, reused: bool) -> dict[str, Any]:
    return {
        "review_id": packet.get("review_id"),
        "resource": f"tide://reviews/{packet.get('review_id')}",
        "files": list(packet.get("files") or []),
        "diff_bytes": int((packet.get("diff") or {}).get("bytes", 0)),
        "diff_truncated": bool((packet.get("diff") or {}).get("truncated", False)),
        "validation_count": len(packet.get("validations") or []),
        "stale_validation_count": int(packet.get("stale_validation_count", 0)),
        "review_focus": list(packet.get("review_focus") or []),
        "review_mode": packet.get("review_mode"),
        "review_base_id": packet.get("review_base_id"),
        "full_task_file_count": len(packet.get("full_task_files") or []),
        "segment_id": packet.get("segment_id"),
        "reused": reused,
    }


def create_review_packet(
    root: Path,
    *,
    full: bool = False,
    full_reason: str | None = None,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before review")
    _ensure_defaults(runtime)
    task_files = _core()._task_files(root, runtime)
    current_fingerprint = diff_fingerprint(root, task_files)
    pending = runtime.get("pending_review")
    if isinstance(pending, dict) and pending.get("diff_fingerprint") == current_fingerprint:
        try:
            packet = _artifacts.read_review_packet(root, str(pending.get("review_id")))
        except TideError:
            packet = None
        if isinstance(packet, dict) and not packet.get("submission"):
            return _packet_summary(packet, reused=True)

    state = _agility._apply_budget(runtime)
    if state.get("split_required"):
        if not _grant_available(runtime):
            authorized = set(runtime.get("authorized_hardgates", []))
            authorized.discard("extended_investigation")
            runtime["authorized_hardgates"] = sorted(authorized)
            save_runtime(root, runtime)
            raise TideError("extended investigation review allowance expired; split the task or obtain a new explicit authorization")

    packet = review_packet(root, full=full, full_reason=full_reason)
    summary = _artifacts.save_review_packet(root, packet)
    packet = _artifacts.read_review_packet(root, str(summary["review_id"]))
    runtime = load_runtime(root)
    _ensure_defaults(runtime)
    runtime["pending_review"] = {
        "review_id": summary["review_id"],
        "diff_fingerprint": current_fingerprint,
        "segment_id": runtime.get("segment_id"),
        "read_count": 0,
        "created_at": _now_iso(),
    }
    _metrics(runtime)["review_packets"] += 1
    if runtime.get("split_required") and isinstance(runtime.get("extended_investigation_grant"), dict):
        grant = runtime["extended_investigation_grant"]
        grant["remaining_review_packets"] = max(0, int(grant.get("remaining_review_packets", 0)) - 1)
    save_runtime(root, runtime)
    return {**summary, "review_mode": packet.get("review_mode"), "review_base_id": packet.get("review_base_id"), "full_task_file_count": len(packet.get("full_task_files") or []), "segment_id": packet.get("segment_id"), "reused": False}


def get_review_packet(root: Path, review_id: str) -> dict[str, Any]:
    packet = _ORIGINALS["get_review_packet"](root, review_id)
    runtime = load_runtime(root)
    if runtime:
        _ensure_defaults(runtime)
        pending = runtime.get("pending_review")
        if isinstance(pending, dict) and pending.get("review_id") == review_id and not packet.get("submission"):
            if int(pending.get("read_count", 0)) > 0:
                _metrics(runtime)["review_cancelled"] += 1
            pending["read_count"] = int(pending.get("read_count", 0)) + 1
            pending["last_read_at"] = _now_iso()
            _metrics(runtime)["review_attempts"] += 1
            _agility._apply_budget(runtime)
            save_runtime(root, runtime)
    return packet


def _finalize_review_metadata(root: Path, review: dict[str, Any]) -> dict[str, Any]:
    runtime = load_runtime(root)
    _ensure_defaults(runtime)
    _apply_segment_metadata(runtime, review)
    runtime["review"] = review
    runtime["pending_review"] = None
    _dedupe_followups(runtime)
    _agility._apply_budget(runtime)
    save_runtime(root, runtime)
    return review


def record_review(
    root: Path,
    *,
    approved: bool,
    findings: list[Any],
    review_id: str | None = None,
) -> dict[str, Any]:
    review = _ORIGINALS["record_review"](
        root,
        approved=approved,
        findings=findings,
        review_id=review_id,
    )
    return _finalize_review_metadata(root, review)


def submit_review(
    root: Path,
    *,
    review_id: str,
    submission_token: str,
    approved: bool,
    findings: list[Any],
) -> dict[str, Any]:
    review = _ORIGINALS["submit_review"](
        root,
        review_id=review_id,
        submission_token=submission_token,
        approved=approved,
        findings=findings,
    )
    return _finalize_review_metadata(root, review)


def _next_action(blockers: list[str], pending_hardgates: list[str]) -> str:
    if pending_hardgates:
        return "authorize pending hardgates: " + ", ".join(pending_hardgates)
    if blockers:
        first = blockers[0]
        if "validation" in first:
            return "run the missing or failed validation for the affected files"
        if "review" in first:
            return "complete the current review without expanding scope"
        if "boundary" in first:
            return "acknowledge external changes or correct the task boundary"
        return first
    return "closure ready"


def check(root: Path) -> dict[str, Any]:
    report = _ORIGINALS["check"](root)
    runtime = load_runtime(root)
    _ensure_defaults(runtime)
    pending = sorted(set(runtime.get("hardgates", [])) - set(runtime.get("authorized_hardgates", [])))
    blockers = list(report.get("blockers", []))
    report["primary_blocker"] = blockers[0] if blockers else None
    report["pending_hardgates"] = pending
    report["next_action"] = _next_action(blockers, pending)
    report["segment_id"] = runtime.get("segment_id")
    report["segment_index"] = runtime.get("segment_index")
    return report


def preparation_report(
    root: Path,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = runtime or load_runtime(root)
    _ensure_defaults(runtime)
    report = _ORIGINALS["preparation_report"](root, runtime)
    pending = list(report.get("pending_hardgates", []))
    report.update(
        {
            "segment_id": runtime.get("segment_id"),
            "segment_index": runtime.get("segment_index"),
            "parent_segment_id": runtime.get("parent_segment_id"),
            "segment_started_at": runtime.get("segment_started_at"),
            "segment_history_count": len(runtime.get("segment_history", [])),
            "boundary_signature": runtime.get("boundary_signature"),
            "pending_review": runtime.get("pending_review"),
            "extended_investigation_grant": runtime.get("extended_investigation_grant"),
            "follow_up_records": list(runtime.get("follow_up_records", [])),
            "pending_hardgates": pending,
        }
    )
    if pending:
        report["next_action"] = "authorize pending hardgates: " + ", ".join(pending)
    return report


def handoff(root: Path) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("no active Tide task")
    report = preparation_report(root, runtime)
    current_validations = _agility._current_validations(root, runtime)
    latest = _latest_review(runtime)
    blocking = []
    if isinstance(latest, dict):
        blocking = [
            item.get("message")
            for item in latest.get("findings", [])
            if isinstance(item, dict) and item.get("severity") == "blocking"
        ]
    return {
        "task": report.get("task"),
        "mode": report.get("mode"),
        "segment_id": report.get("segment_id"),
        "segment_index": report.get("segment_index"),
        "boundary": report.get("boundary"),
        "changed_files": _core()._task_files(root, runtime),
        "pending_hardgates": report.get("pending_hardgates"),
        "split_required": report.get("split_required"),
        "split_reasons": report.get("split_reasons"),
        "closure_locked": report.get("closure_locked"),
        "current_validations": [
            {
                "command": item.get("command"),
                "phase": item.get("phase"),
                "passed": item.get("passed"),
                "files": item.get("files"),
                "log_id": item.get("log_id"),
            }
            for item in current_validations
        ],
        "last_review_id": latest.get("review_id") if latest else None,
        "last_blockers": blocking,
        "follow_up_records": report.get("follow_up_records"),
        "next_action": report.get("next_action"),
    }


def list_review_resources(root: Path) -> list[dict[str, str]]:
    resources = _ORIGINAL_LIST_REVIEW_RESOURCES(root)
    runtime = load_runtime(root)
    keep: set[str] = set()
    if runtime:
        pending = runtime.get("pending_review")
        if isinstance(pending, dict) and pending.get("review_id"):
            keep.add(str(pending["review_id"]))
        latest = _latest_review(runtime)
        if latest and latest.get("review_id"):
            keep.add(str(latest["review_id"]))
    selected = [item for item in resources if item.get("name") in keep]
    for item in reversed(resources):
        if item not in selected:
            selected.append(item)
        if len(selected) >= 5:
            break
    return list(reversed(selected[:5]))
