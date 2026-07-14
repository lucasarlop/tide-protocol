from __future__ import annotations

from pathlib import Path
from typing import Any

from .evidence import (
    approval_proof, approved_commit_is_current, current_validations,
    effective_validations, missing_required_validations,
    required_validation_status, simplicity_signals, uncovered_files,
)
from .locks import _matches, matching_locks
from .policy import PolicyDecision, decide
from .project import changed_files, file_fingerprints, load_runtime, save_runtime

def _normalize_strings(values: list[str] | None) -> list[str]:
    return sorted(dict.fromkeys(str(value).strip() for value in (values or []) if str(value).strip()))


def _inside(path: str, boundary: list[str]) -> bool:
    return any(_matches(path, pattern) for pattern in boundary)


def _task_files(root: Path, state: dict[str, Any]) -> list[str]:
    boundary = list(state.get("boundary") or [])
    if not boundary:
        return []
    return sorted(path for path in changed_files(root) if _inside(path, boundary))


def _outside_violations(root: Path, state: dict[str, Any]) -> list[str]:
    boundary = list(state.get("boundary") or [])
    baseline = dict(state.get("baseline_fingerprints") or {})
    acknowledgements = dict(state.get("external_acknowledgements") or {})
    violations: list[str] = []
    for path in changed_files(root):
        if _inside(path, boundary):
            continue
        current = file_fingerprints(root, [path])[path]
        acknowledged = acknowledgements.get(path)
        if acknowledged == current:
            continue
        if baseline.get(path) != current:
            violations.append(path)
    return sorted(violations)


def _policy(root: Path, state: dict[str, Any], task_files: list[str] | None = None) -> PolicyDecision:
    files = task_files if task_files is not None else list(state.get("boundary") or [])
    locks = matching_locks(root, files or list(state.get("boundary") or []))
    return decide(str(state.get("task") or ""), files, locks)


def _required_validations(root: Path, state: dict[str, Any], task_files: list[str]) -> list[str]:
    locks = matching_locks(root, task_files or list(state.get("boundary") or []))
    return _normalize_strings([
        *list(state.get("required_validations") or []),
        *(command for lock in locks for command in lock.validations),
    ])


def _authorization_request(pending: list[str]) -> dict[str, Any] | None:
    if not pending:
        return None
    return {
        "tool": "authorize",
        "arguments": {"gates": pending, "all": False},
        "interaction": "client_permission_prompt",
        "message": "Authorize the pending Tide decisions.",
    }


def _convergence_decision_request(state: dict[str, Any]) -> dict[str, Any] | None:
    convergence = state.get("convergence") or {}
    if convergence.get("status") != "investigation_checkpoint":
        return None
    return {
        "kind": "investigation_continuation",
        "question": "Continue for one bounded investigation cycle or stop with the current diagnosis?",
        "options": ["continue_one_cycle", "stop_and_report"],
        "recommendation": "continue_one_cycle" if convergence.get("next_step") else "stop_and_report",
        "evidence": list(convergence.get("evidence") or [])[-5:],
        "next_step": convergence.get("next_step"),
    }


def evaluate_state(root: Path, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state if state is not None else load_runtime(root)
    if not state:
        return {
            "active": False,
            "lifecycle": "idle",
            "ready": False,
            "blockers": ["no active Tide task"],
            "primary_blocker": "no active Tide task",
            "next_action": "prepare a bounded task from the user's request",
            "agent_should_continue": True,
            "user_action_required": False,
            "authorization_request": None,
            "decision_request": None,
        }

    if state.get("lifecycle") == "approved" and approved_commit_is_current(root, state):
        state["lifecycle"] = "committed"
        save_runtime(root, state)

    lifecycle = str(state.get("lifecycle") or "active")
    if lifecycle == "committed":
        approved = state.get("approved_snapshot") or {}
        files = sorted((approved.get("files") or {}).keys())
        return {
            "active": True,
            "task": state.get("task"),
            "task_id": state.get("task_id"),
            "lifecycle": "committed",
            "ready": True,
            "files": files,
            "changed_files": [],
            "boundary": list(state.get("boundary") or []),
            "blockers": [],
            "primary_blocker": None,
            "next_action": "task committed; a new task may be prepared",
            "agent_should_continue": False,
            "user_action_required": False,
            "authorization_request": None,
            "decision_request": None,
            "approval_proof": {
                "type": "current_review",
                "review_id": approved.get("review_id"),
                "segment_id": (state.get("segments") or {}).get("current_id"),
            },
        }
    if lifecycle == "abandoned":
        return {
            "active": True,
            "task": state.get("task"),
            "task_id": state.get("task_id"),
            "lifecycle": "abandoned",
            "ready": False,
            "blockers": [],
            "primary_blocker": None,
            "next_action": "task abandoned; a new task may be prepared",
            "agent_should_continue": False,
            "user_action_required": False,
            "authorization_request": None,
            "decision_request": None,
        }

    task_files = _task_files(root, state)
    outside = _outside_violations(root, state)
    policy = _policy(root, state, task_files)
    locks = matching_locks(root, task_files or list(state.get("boundary") or []))
    required = _required_validations(root, state, task_files)
    validations = effective_validations(root, state)
    current_all = current_validations(root, state)
    missing = missing_required_validations(required, validations)
    uncovered = uncovered_files(task_files, validations)
    failures = [item for item in validations if not item.get("passed")]
    stale_count = max(0, len(state.get("validations", [])) - len(current_all))
    simplicity = simplicity_signals(root, task_files)
    review_required = policy.review_required or bool(simplicity)
    review_level = "critical" if policy.review_level == "critical" or simplicity else "normal"
    proof = approval_proof(root, state, task_files)
    review = state.get("review") if isinstance(state.get("review"), dict) else None
    current_fps = file_fingerprints(root, task_files) if task_files else {}
    review_current = bool(
        review
        and isinstance(review.get("file_fingerprints"), dict)
        and review.get("file_fingerprints") == current_fps
    )
    blocking_findings = [
        item
        for item in (review or {}).get("findings", [])
        if isinstance(item, dict) and item.get("severity") == "blocking"
    ]

    stored_policy = state.get("policy") if isinstance(state.get("policy"), dict) else {}
    authorization_gates = sorted(
        set(policy.authorization_gates) | set(stored_policy.get("authorization_gates") or [])
    )
    risk_signals = sorted(
        set(policy.risk_signals) | set(stored_policy.get("risk_signals") or [])
    )
    pending = sorted(set(authorization_gates) - set(state.get("authorizations") or []))
    decision_request = _convergence_decision_request(state)
    convergence = state.get("convergence") or {}
    convergence_status = str(convergence.get("status") or "progressing")

    blockers: list[str] = []
    boundary = list(state.get("boundary") or [])
    if not boundary:
        blockers.append("no boundary declared")
    if outside:
        blockers.append("files changed outside the declared boundary")
    if pending:
        blockers.append("user authorization is required")
    if task_files and uncovered:
        blockers.append("no current validation evidence covers the changed task files")
    if failures:
        blockers.append("one or more current validations failed")
    if missing:
        blockers.append("required validations are missing for their covered files")
    if review_required and proof is None:
        if review_current and blocking_findings:
            blockers.append("independent review has blocking findings")
        elif review and not review_current:
            blockers.append("independent review is stale for the current diff")
        else:
            blockers.append("independent review required")
    if not task_files and boundary and state.get("approved_snapshot") is None:
        blockers.append("no implementation changes are present in the task boundary")
    if convergence_status == "investigation_checkpoint":
        blockers.append("investigation continuation decision required")
    elif convergence_status == "stop_requested":
        blockers.append("investigation stopped without a completed implementation")
    elif convergence_status == "externally_blocked":
        blockers.append("external dependency prevents further progress")

    blockers = list(dict.fromkeys(blockers))
    user_action_required = bool(pending or decision_request)
    can_stop = convergence_status in {"stop_requested", "externally_blocked"}
    ready = not blockers and bool(task_files or lifecycle == "approved")

    if pending:
        next_action = "call authorize for the pending user decisions"
    elif decision_request:
        next_action = "ask the user whether to continue one bounded investigation cycle or stop and report"
    elif convergence_status == "stop_requested":
        next_action = "report the current diagnosis, evidence, remaining uncertainty, and that no commit was made"
    elif convergence_status == "externally_blocked":
        next_action = "report the missing external dependency and the exact condition required to continue"
    elif not boundary:
        next_action = "inspect the live code and call revise with the smallest safe boundary before editing"
    elif outside:
        next_action = "restore unrelated changes or add only the genuinely required files to the boundary"
    elif convergence_status == "investigating":
        next_action = str(convergence.get("next_step") or "stop editing and perform one bounded root-cause investigation")
    elif failures:
        next_action = "inspect the saved failure summary, fix the cause, and rerun only the smallest affected validation"
    elif uncovered:
        next_action = "validate uncovered files: " + ", ".join(uncovered[:5])
    elif missing:
        next_action = "run mandatory validation: " + missing[0]
    elif blocking_findings:
        next_action = "fix only the listed blocking findings, then run targeted validation"
    elif review_required and proof is None:
        next_action = "create an independent review packet and run the selected reviewer"
    elif ready:
        next_action = "closure ready; wait for commit authorization if a commit is requested"
    else:
        next_action = "implement the smallest safe delta"

    state["lifecycle"] = "approved" if proof is not None else "active"
    state["policy"] = {
        "authorization_gates": authorization_gates,
        "risk_signals": risk_signals,
        "review_required": review_required,
        "review_level": review_level,
        "reasons": list(dict.fromkeys([*policy.reasons, *simplicity])),
    }
    save_runtime(root, state)

    return {
        "active": True,
        "task": state.get("task"),
        "task_id": state.get("task_id"),
        "lifecycle": state.get("lifecycle"),
        "ready": ready,
        "status": "ready" if ready else "blocked",
        "files": task_files,
        "changed_files": task_files,
        "all_worktree_changes": changed_files(root),
        "boundary": boundary,
        "outside_boundary": outside,
        "locks": [lock.name for lock in locks],
        "required_validations": required,
        "required_validation_status": required_validation_status(required, validations),
        "missing_validations": missing,
        "missing_required_validations": missing,
        "uncovered_validation_files": uncovered,
        "current_validation_count": len(validations),
        "stale_validation_count": stale_count,
        "failed_validation_count": len(failures),
        "review_required": review_required,
        "review_level": review_level,
        "review_current": review_current,
        "review": review,
        "approval_proof": proof,
        "pending_hardgates": pending,
        "authorization_gates": authorization_gates,
        "risk_signals": risk_signals,
        "review_reasons": list(dict.fromkeys([*policy.reasons, *simplicity])),
        "convergence": dict(convergence),
        "blockers": blockers,
        "primary_blocker": blockers[0] if blockers else None,
        "next_action": next_action,
        "agent_should_continue": not ready and not user_action_required and not can_stop,
        "user_action_required": user_action_required,
        "authorization_request": _authorization_request(pending),
        "decision_request": decision_request,
        "mutation_allowed": bool(boundary) and not pending and not decision_request and not can_stop,
        "split_recommended": len(task_files) > 20 or len(blocking_findings) > 5,
    }
