from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .evidence import approval_proof, content_fingerprints, evidence_is_current
from .git_gate import commit_check as _commit_gate, ensure_commit_hook
from .locks import matching_locks
from .policy import decide
from .project import TideError, changed_files, diff_fingerprint, file_fingerprints, load_runtime, save_runtime
from .review import _archive_review
from .rules import (
    _inside, _normalize_strings, _outside_violations, _policy, _task_files,
    evaluate_state,
)
from .state import archive_summary, new_task_state, now_iso

def prepare(
    root: Path,
    task: str,
    files: list[str] | None = None,
    required_validations: list[str] | None = None,
) -> dict[str, Any]:
    task = task.strip()
    if not task:
        raise TideError("prepare requires a concrete task")
    existing = load_runtime(root)
    archive: list[dict[str, Any]] = []
    if existing:
        if existing.get("lifecycle") in {"active", "approved"}:
            if str(existing.get("task") or "").strip() == task:
                return {**evaluate_state(root, existing), "reused": True}
            raise TideError(
                "another Tide task is active; call resume to continue it or explicitly abandon it before preparing a new task"
            )
        archive = list(existing.get("archive") or [])
        archive.append(archive_summary(existing, outcome=str(existing.get("lifecycle") or "closed")))

    boundary = _normalize_strings(files)
    baseline_files = changed_files(root)
    baseline_fingerprints = file_fingerprints(root, baseline_files)
    policy = decide(task, boundary, matching_locks(root, boundary))
    policy_value = {
        "authorization_gates": list(policy.authorization_gates),
        "risk_signals": list(policy.risk_signals),
        "review_required": policy.review_required,
        "review_level": policy.review_level,
        "reasons": list(policy.reasons),
    }
    dirty_boundary = sorted(path for path in baseline_files if _inside(path, boundary))
    if dirty_boundary:
        policy_value["authorization_gates"] = sorted(
            set(policy_value["authorization_gates"]) | {"dirty_boundary"}
        )
        policy_value["reasons"].append("pre-existing changes overlap the declared boundary")

    state = new_task_state(
        task=task,
        boundary=boundary,
        baseline_files=baseline_files,
        baseline_fingerprints=baseline_fingerprints,
        required_validations=_normalize_strings(required_validations),
        policy=policy_value,
    )
    state["archive"] = archive
    save_runtime(root, state)
    return preparation_report(root, state)


def revise(
    root: Path,
    *,
    task: str | None = None,
    add_files: list[str] | None = None,
    remove_files: list[str] | None = None,
    add_required_validations: list[str] | None = None,
    remove_required_validations: list[str] | None = None,
) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before revise")
    if state.get("lifecycle") in {"committed", "abandoned"}:
        raise TideError("the current Tide task is closed; prepare a new task")

    previous_validations = [dict(item) for item in state.get("validations", []) if isinstance(item, dict)]
    _archive_review(state)
    boundary = set(state.get("boundary") or [])
    boundary.update(_normalize_strings(add_files))
    boundary.difference_update(_normalize_strings(remove_files))
    state["boundary"] = sorted(boundary)
    if task is not None:
        state["task"] = task.strip()
    required = set(_normalize_strings(state.get("required_validations") or []))
    required.update(_normalize_strings(add_required_validations))
    required.difference_update(_normalize_strings(remove_required_validations))
    state["required_validations"] = sorted(required)
    state["revision"] = int(state.get("revision", 0)) + 1
    state["review"] = None
    state["pending_review"] = None
    state["approved_snapshot"] = None
    state["lifecycle"] = "active"
    state["operational_mode"] = False

    task_files = _task_files(root, state)
    preserved = [
        item
        for item in previous_validations
        if item.get("passed")
        and set(str(path) for path in item.get("files", [])) <= set(task_files)
        and evidence_is_current(root, item)
    ]
    state["validations"] = preserved

    added_dirty = [
        path
        for path in state.get("baseline_files", [])
        if _inside(path, state["boundary"])
        and path not in set(state.get("authorizations") or [])
    ]
    policy = _policy(root, state, task_files)
    state["policy"] = {
        "authorization_gates": sorted(
            set(policy.authorization_gates) | ({"dirty_boundary"} if added_dirty else set())
        ),
        "risk_signals": list(policy.risk_signals),
        "review_required": policy.review_required,
        "review_level": policy.review_level,
        "reasons": list(policy.reasons),
    }
    save_runtime(root, state)
    return preparation_report(root, state)


def authorize(
    root: Path,
    gates: list[str] | None = None,
    *,
    all_gates: bool = False,
) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before authorization")
    evaluation = evaluate_state(root, state)
    known = set(evaluation.get("pending_hardgates") or []) | set(state.get("authorizations") or [])
    requested = set(evaluation.get("pending_hardgates") or []) if all_gates else set(gates or [])
    unknown = sorted(requested - known)
    if unknown:
        raise TideError("unknown authorization gates: " + ", ".join(unknown))
    state["authorizations"] = sorted(set(state.get("authorizations") or []) | requested)
    save_runtime(root, state)
    return preparation_report(root, state)


def abandon(root: Path, *, reason: str) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("no active Tide task")
    if not reason.strip():
        raise TideError("abandon requires a reason")
    state["lifecycle"] = "abandoned"
    state["abandoned_reason"] = reason.strip()
    save_runtime(root, state)
    return evaluate_state(root, state)


def split(root: Path, *, task: str, files: list[str]) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before splitting")
    target = _normalize_strings(files)
    current_files = _task_files(root, state)
    selected = [path for path in current_files if _inside(path, target)]
    if not selected:
        raise TideError("split boundary does not contain any changed file from the current task")
    proof = approval_proof(root, state, current_files)
    if proof is not None and set(selected) == set(current_files):
        raise TideError("split not required: the current fingerprint is already approved; proceed to commit_check")

    segments = state.setdefault("segments", {})
    history = list(segments.get("history") or [])
    history.append(
        {
            "segment_id": segments.get("current_id"),
            "task": state.get("task"),
            "boundary": list(state.get("boundary") or []),
            "files": current_files,
            "closed_at": now_iso(),
        }
    )
    receipts = list(segments.get("receipts") or [])
    if proof is not None:
        receipts.append(
            {
                "segment_id": segments.get("current_id"),
                "files": file_fingerprints(root, current_files),
                "review_id": proof.get("review_id"),
                "approved_at": now_iso(),
            }
        )

    previous_validations = list(state.get("validations") or [])
    state["task"] = task.strip()
    state["boundary"] = target
    state["review"] = None
    state["pending_review"] = None
    state["approved_snapshot"] = None
    state["lifecycle"] = "active"
    state["convergence"] = {
        "status": "progressing",
        "failed_attempts": 0,
        "investigation_cycles": 0,
        "cycle_grants": 0,
        "cycle_active": False,
        "root_cause_known": None,
        "last_progress": None,
        "evidence": [],
        "next_step": None,
        "decision": None,
    }
    state["segments"] = {
        "current_id": f"segment-{uuid.uuid4().hex[:12]}",
        "index": int(segments.get("index", 0)) + 1,
        "history": history,
        "receipts": receipts,
    }
    child_files = _task_files(root, state)
    inherited: list[dict[str, Any]] = []
    current_fps = file_fingerprints(root, child_files)
    for item in previous_validations:
        if not item.get("passed"):
            continue
        expected = item.get("coverage_fingerprints")
        if not isinstance(expected, dict) or not set(child_files) <= set(expected):
            continue
        if {path: expected[path] for path in child_files} != current_fps:
            continue
        narrowed = dict(item)
        narrowed["files"] = child_files
        narrowed["covers"] = child_files
        narrowed["coverage_fingerprints"] = current_fps
        narrowed["diff_fingerprint"] = diff_fingerprint(root, child_files)
        narrowed["inherited_from_parent_segment"] = True
        inherited.append(narrowed)
    state["validations"] = inherited
    save_runtime(root, state)
    return {
        **preparation_report(root, state),
        "inherited_validation_count": len(inherited),
        "segment_receipt_count": len(receipts),
    }


def reopen(root: Path, *, reason: str, code_change_required: bool = False) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before reopen")
    if not reason.strip():
        raise TideError("reopen requires a concrete reason")
    if state.get("lifecycle") == "approved" and not code_change_required:
        state["operational_mode"] = True
        state["operational_reason"] = reason.strip()
        save_runtime(root, state)
        result = preparation_report(root, state)
        result["next_action"] = "run operational checks without changing approved code"
        return result
    _archive_review(state)
    state["review"] = None
    state["pending_review"] = None
    state["approved_snapshot"] = None
    state["lifecycle"] = "active"
    state["operational_mode"] = False
    state["reopen_reason"] = reason.strip()
    state["convergence"]["status"] = "progressing"
    save_runtime(root, state)
    return preparation_report(root, state)


def operational_verify(root: Path, *, name: str, passed: bool, details: str = "") -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before operational verification")
    record = {
        "name": name.strip(),
        "passed": bool(passed),
        "details": details.strip()[:1000],
        "recorded_at": now_iso(),
    }
    state.setdefault("operational_checks", []).append(record)
    save_runtime(root, state)
    return record


def external_acknowledge(root: Path, files: list[str], *, reason: str) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        raise TideError("run Tide prepare before acknowledging external changes")
    if not reason.strip():
        raise TideError("external acknowledgement requires a reason")
    acknowledgements = state.setdefault("external_acknowledgements", {})
    for path in files:
        if _inside(path, list(state.get("boundary") or [])):
            raise TideError(f"cannot acknowledge a file inside the task boundary: {path}")
        acknowledgements[path] = file_fingerprints(root, [path])[path]
    state["external_acknowledgement_reason"] = reason.strip()
    save_runtime(root, state)
    report = check(root)
    report["acknowledged_external_changes"] = [
        {"file": path, "reason": reason.strip()} for path in sorted(files)
    ]
    return report


def preparation_report(root: Path, state: dict[str, Any] | None = None) -> dict[str, Any]:
    return evaluate_state(root, state)


def check(root: Path) -> dict[str, Any]:
    return evaluate_state(root)


def resume(root: Path) -> dict[str, Any]:
    hook = ensure_commit_hook(root)
    evaluation = evaluate_state(root)
    if not evaluation.get("active"):
        return {**evaluation, "commit_hook": hook}
    return {
        "active": True,
        "task": evaluation.get("task"),
        "task_id": evaluation.get("task_id"),
        "lifecycle": evaluation.get("lifecycle"),
        "boundary": evaluation.get("boundary", []),
        "changed_files": evaluation.get("files", []),
        "primary_blocker": evaluation.get("primary_blocker"),
        "blockers": evaluation.get("blockers", []),
        "next_action": evaluation.get("next_action"),
        "ready": evaluation.get("ready"),
        "agent_should_continue": evaluation.get("agent_should_continue"),
        "user_action_required": evaluation.get("user_action_required"),
        "authorization_request": evaluation.get("authorization_request"),
        "decision_request": evaluation.get("decision_request"),
        "review_level": evaluation.get("review_level"),
        "risk_signals": evaluation.get("risk_signals", []),
        "convergence": evaluation.get("convergence", {}),
        "commit_hook": hook,
    }


def handoff(root: Path) -> dict[str, Any]:
    return resume(root)


def commit_check(root: Path) -> dict[str, Any]:
    evaluation = evaluate_state(root)
    state = load_runtime(root)
    return _commit_gate(root, evaluation, _task_files(root, state) if state else [])
