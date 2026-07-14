from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .artifacts import consume_review_submission, read_review_packet, save_review_packet
from .evidence import content_fingerprints, effective_validations, latest_review
from .locks import matching_locks
from .project import TideError, current_diff, diff_fingerprint, file_fingerprints, load_runtime, save_runtime
from .rules import _task_files, evaluate_state
from .state import now_iso

def review_packet(root: Path, *, full: bool = False, full_reason: str | None = None) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before review")
    evaluation = evaluate_state(root, state)
    if evaluation.get("user_action_required"):
        raise TideError("review cannot start while a user decision is pending")
    if evaluation.get("uncovered_validation_files"):
        raise TideError(
            "review requires validation coverage for: "
            + ", ".join(evaluation["uncovered_validation_files"])
        )
    if evaluation.get("missing_required_validations"):
        raise TideError(
            "review requires mandatory validation: "
            + "; ".join(evaluation["missing_required_validations"])
        )
    task_files = list(evaluation.get("files") or [])
    if not task_files:
        raise TideError("review requires a changed task delta")
    if evaluation.get("approval_proof"):
        raise TideError("current fingerprint is already approved; no additional review is allowed")

    fingerprint = diff_fingerprint(root, task_files)
    pending = state.get("pending_review")
    if isinstance(pending, dict) and pending.get("diff_fingerprint") == fingerprint:
        packet = read_review_packet(root, str(pending.get("review_id")))
        return packet

    previous = latest_review(state)
    current_fps = file_fingerprints(root, task_files)
    previous_fps = previous.get("file_fingerprints", {}) if isinstance(previous, dict) else {}
    if previous_fps:
        review_files = [path for path in task_files if previous_fps.get(path) != current_fps.get(path)]
    else:
        review_files = task_files
    if not review_files:
        raise TideError("no changed files remain since the latest review")

    review_level = str(evaluation.get("review_level") or "normal")
    review_mode = "full" if full else "incremental"
    if full and previous and not str(full_reason or "").strip():
        raise TideError("full review after an existing review requires full_reason")
    reviewer_agent = "tide-reviewer-critical" if review_level == "critical" or full else "tide-reviewer"
    locks = matching_locks(root, review_files)
    packet = {
        "task": state.get("task"),
        "task_id": state.get("task_id"),
        "boundary": list(state.get("boundary") or []),
        "files": review_files,
        "all_task_files": task_files,
        "file_fingerprints": current_fps,
        "diff_fingerprint": fingerprint,
        "diff": current_diff(root, review_files),
        "validations": effective_validations(root, state),
        "required_validations": evaluation.get("required_validations", []),
        "review_focus": list(evaluation.get("review_reasons") or []),
        "review_level": review_level,
        "review_mode": review_mode,
        "reviewer_agent": reviewer_agent,
        "full_reason": full_reason,
        "previous_blocking_findings": [
            item
            for item in (previous or {}).get("findings", [])
            if isinstance(item, dict) and item.get("severity") == "blocking"
        ],
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
        "instruction": "Review only. Submit the verdict directly with review_submit. Do not ask the writer to relay it.",
    }
    summary = save_review_packet(root, packet)
    state["pending_review"] = {
        "review_id": summary["review_id"],
        "diff_fingerprint": fingerprint,
        "review_mode": review_mode,
        "reviewer_agent": reviewer_agent,
    }
    save_runtime(root, state)
    return {
        **summary,
        "review_mode": review_mode,
        "review_level": review_level,
        "reviewer_agent": reviewer_agent,
        "reviewer_submits_verdict": True,
        "writer_must_not_resubmit": True,
    }


def create_review_packet(root: Path, *, full: bool = False, full_reason: str | None = None) -> dict[str, Any]:
    result = review_packet(root, full=full, full_reason=full_reason)
    if "submission_token" in result:
        return {
            key: value
            for key, value in result.items()
            if key not in {"diff", "submission_token", "submission"}
        }
    return result


def get_review_packet(root: Path, review_id: str) -> dict[str, Any]:
    packet = read_review_packet(root, review_id)
    state = load_runtime(root)
    task_files = _task_files(root, state) if state else []
    return {
        **packet,
        "current": packet.get("diff_fingerprint") == diff_fingerprint(root, task_files),
    }


def submit_review(
    root: Path,
    *,
    review_id: str,
    submission_token: str,
    approved: bool,
    findings: list[Any],
) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before review")
    packet = read_review_packet(root, review_id)
    task_files = _task_files(root, state)
    fingerprint = diff_fingerprint(root, task_files)
    if packet.get("diff_fingerprint") != fingerprint:
        raise TideError("review packet is stale for the current diff")
    normalized = _normalize_findings(findings, approved=approved)
    blocking = [item for item in normalized if item["severity"] == "blocking"]
    if approved and blocking:
        raise TideError("an approved review cannot contain blocking findings")
    if approved and bool((packet.get("diff") or {}).get("truncated")):
        raise TideError("cannot approve a truncated review packet")
    actual_approved = bool(approved and not blocking)
    review = {
        "review_id": review_id,
        "approved": actual_approved,
        "findings": normalized,
        "created_at": now_iso(),
        "files": task_files,
        "file_fingerprints": file_fingerprints(root, task_files),
        "diff_fingerprint": fingerprint,
        "review_mode": packet.get("review_mode"),
        "review_level": packet.get("review_level"),
        "segment_id": (state.get("segments") or {}).get("current_id"),
    }
    receipt = consume_review_submission(root, review_id, submission_token, review)
    review["receipt_id"] = receipt["receipt_id"]
    _archive_review(state)
    state["review"] = review
    state["pending_review"] = None
    followups = [item for item in normalized if item["severity"] == "follow_up"]
    state["follow_up_tasks"] = [*state.get("follow_up_tasks", []), *followups]
    if actual_approved:
        state["approved_snapshot"] = {
            "fingerprint": fingerprint,
            "files": file_fingerprints(root, task_files),
            "content": content_fingerprints(root, task_files),
            "review_id": review_id,
            "approved_at": now_iso(),
        }
        state["lifecycle"] = "approved"
        state["convergence"]["status"] = "progressing"
    else:
        state["approved_snapshot"] = None
        state["lifecycle"] = "active"
    save_runtime(root, state)
    return {
        **review,
        "blocking_findings": blocking,
        "follow_up_findings": followups,
        "verdict_submitted": True,
        "idempotent": False,
    }


def record_review(
    root: Path,
    *,
    approved: bool,
    findings: list[Any],
    review_id: str | None = None,
) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before review")
    task_files = _task_files(root, state)
    fingerprint = diff_fingerprint(root, task_files)
    if review_id:
        packet = read_review_packet(root, review_id)
        if packet.get("diff_fingerprint") != fingerprint:
            raise TideError("review packet is stale for the current diff")
    normalized = _normalize_findings(findings, approved=approved)
    blocking = [item for item in normalized if item["severity"] == "blocking"]
    actual = bool(approved and not blocking)
    review = {
        "review_id": review_id or f"manual-review-{uuid.uuid4().hex[:12]}",
        "approved": actual,
        "findings": normalized,
        "created_at": now_iso(),
        "files": task_files,
        "file_fingerprints": file_fingerprints(root, task_files),
        "diff_fingerprint": fingerprint,
        "review_mode": "manual",
        "review_level": evaluate_state(root, state).get("review_level"),
        "segment_id": (state.get("segments") or {}).get("current_id"),
    }
    _archive_review(state)
    state["review"] = review
    if actual:
        state["approved_snapshot"] = {
            "fingerprint": fingerprint,
            "files": file_fingerprints(root, task_files),
            "content": content_fingerprints(root, task_files),
            "review_id": review["review_id"],
            "approved_at": now_iso(),
        }
        state["lifecycle"] = "approved"
    else:
        state["approved_snapshot"] = None
        state["lifecycle"] = "active"
    save_runtime(root, state)
    return review


def _normalize_findings(findings: list[Any], *, approved: bool) -> list[dict[str, Any]]:
    aliases = {
        "blocking": "blocking", "blocker": "blocking", "critical": "blocking", "high": "blocking",
        "follow_up": "follow_up", "follow-up": "follow_up", "medium": "follow_up",
        "info": "info", "low": "info",
    }
    result: list[dict[str, Any]] = []
    for item in findings:
        if isinstance(item, dict):
            message = str(item.get("message") or "").strip()
            severity = aliases.get(str(item.get("severity") or "").strip().lower())
            if not message or not severity:
                raise TideError("structured findings require severity and message")
            finding_id = str(item.get("id") or "").strip() or f"finding-{uuid.uuid4().hex[:8]}"
            result.append(
                {
                    "id": finding_id,
                    "severity": severity,
                    "message": message,
                    "paths": list(item.get("paths") or []),
                    "expected_action": str(item.get("expected_action") or ""),
                }
            )
        else:
            message = str(item).strip()
            if not message:
                continue
            result.append(
                {
                    "id": f"finding-{uuid.uuid4().hex[:8]}",
                    "severity": "info" if approved else "blocking",
                    "message": message,
                    "paths": [],
                    "expected_action": "",
                }
            )
    return result


def _archive_review(state: dict[str, Any]) -> None:
    review = state.get("review")
    if not isinstance(review, dict) or not review.get("review_id"):
        return
    history = state.setdefault("review_history", [])
    if not any(item.get("review_id") == review.get("review_id") for item in history if isinstance(item, dict)):
        history.append(dict(review))
