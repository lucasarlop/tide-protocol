from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .project import (
    TideError,
    diff_fingerprint,
    file_fingerprints,
    load_runtime,
    save_runtime,
)
from .stability import ensure_commit_hook

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Callable[..., Any]] = {}
_BUDGET_GATE = "extended_investigation"
_BUDGET_BLOCKER = "task must be split or extended investigation explicitly authorized"
_REVIEW_BLOCKERS = {
    "independent review required",
    "independent review is stale for the current diff",
}
_COMMIT_REVIEW_BLOCKER = "current task has no approved independent review"
_COMMIT_FINGERPRINT_BLOCKER = "current worktree fingerprint is not the approved fingerprint"


def install(core: ModuleType) -> None:
    global _CORE
    if getattr(core, "_stability_fixes_installed", False):
        return
    _CORE = core
    for name in (
        "split",
        "reopen",
        "authorize",
        "check",
        "preparation_report",
        "resume",
        "commit_check",
    ):
        _ORIGINALS[name] = getattr(core, name)
    core.split = split
    core.reopen = reopen
    core.authorize = authorize
    core.check = check
    core.preparation_report = preparation_report
    core.resume = resume
    core.commit_check = commit_check
    core._stability_fixes_installed = True


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide stability fixes are not installed")
    return _CORE


def _task_files(root: Path, runtime: dict[str, Any]) -> list[str]:
    return list(_core()._task_files(root, runtime))


def _current_fingerprint(root: Path, runtime: dict[str, Any]) -> str:
    return diff_fingerprint(root, _task_files(root, runtime))


def _compatible_receipt(root: Path, runtime: dict[str, Any]) -> dict[str, Any] | None:
    task_files = _task_files(root, runtime)
    if not task_files:
        return None
    current = file_fingerprints(root, task_files)
    for receipt in reversed(runtime.get("segment_receipts", [])):
        if not isinstance(receipt, dict) or not receipt.get("review_id"):
            continue
        expected = receipt.get("files")
        if not isinstance(expected, dict):
            continue
        normalized = {str(path): str(value) for path, value in expected.items()}
        if set(normalized) == set(task_files) and normalized == current:
            return {
                "type": "segment_receipt",
                "review_id": receipt.get("review_id"),
                "segment_id": receipt.get("segment_id"),
            }
    return None


def _approval_proof(root: Path, runtime: dict[str, Any]) -> dict[str, Any] | None:
    review = runtime.get("review") if isinstance(runtime.get("review"), dict) else {}
    approved = str(runtime.get("approved_fingerprint") or "")
    if review.get("approved") and approved and approved == _current_fingerprint(root, runtime):
        return {
            "type": "current_review",
            "review_id": review.get("review_id"),
            "segment_id": runtime.get("segment_id"),
        }
    return _compatible_receipt(root, runtime)


def _approved_current(root: Path, runtime: dict[str, Any]) -> bool:
    return _approval_proof(root, runtime) is not None


def _strip_budget_gate(root: Path, runtime: dict[str, Any]) -> bool:
    if not _approved_current(root, runtime):
        return False
    hardgates = set(runtime.get("hardgates", []))
    authorized = set(runtime.get("authorized_hardgates", []))
    changed = _BUDGET_GATE in hardgates or _BUDGET_GATE in authorized or bool(runtime.get("split_required"))
    hardgates.discard(_BUDGET_GATE)
    authorized.discard(_BUDGET_GATE)
    runtime["hardgates"] = sorted(hardgates)
    runtime["authorized_hardgates"] = sorted(authorized & hardgates)
    runtime["split_required"] = False
    runtime["split_reasons"] = []
    runtime["extended_investigation_grant"] = None
    if changed:
        save_runtime(root, runtime)
    return changed


def _pending(runtime: dict[str, Any]) -> list[str]:
    return sorted(
        set(runtime.get("hardgates", [])) - set(runtime.get("authorized_hardgates", []))
    )


def _normalize_nested_resume(value: dict[str, Any], pending: list[str], *, ready: bool | None = None) -> None:
    nested = value.get("resume")
    if not isinstance(nested, dict):
        return
    nested["pending_hardgates"] = pending
    nested["split_required"] = False
    if ready is True:
        nested["next_action"] = "closure ready"
    value["resume"] = nested


def _normalize_report(root: Path, value: Any, *, closure_check: bool) -> Any:
    if not isinstance(value, dict):
        return value
    runtime = load_runtime(root)
    if not runtime:
        return value
    proof = _approval_proof(root, runtime)
    value["approval_proof"] = proof
    if proof is None:
        if closure_check:
            value["commit_ready"] = False
            value["commit_blockers"] = ["no compatible approval proof"]
        return value

    _strip_budget_gate(root, runtime)
    runtime = load_runtime(root)
    pending = _pending(runtime)
    value["pending_hardgates"] = pending
    value["split_required"] = False
    value["split_reasons"] = []
    if closure_check:
        blockers = [
            str(blocker)
            for blocker in value.get("blockers", [])
            if str(blocker) != _BUDGET_BLOCKER and str(blocker) not in _REVIEW_BLOCKERS
        ]
        blockers = list(dict.fromkeys(blockers))
        ready = not blockers and not pending
        runtime["status"] = "ready" if ready else "blocked"
        save_runtime(root, runtime)
        value["blockers"] = blockers
        value["primary_blocker"] = blockers[0] if blockers else None
        value["ready"] = ready
        value["status"] = runtime["status"]
        value["commit_ready"] = ready
        value["commit_blockers"] = [] if ready else blockers
        if ready:
            value["next_action"] = "closure ready"
        _normalize_nested_resume(value, pending, ready=ready)
    else:
        if not pending:
            value["next_action"] = "closure ready"
        _normalize_nested_resume(value, pending, ready=not pending)
    return value


def split(root: Path, *, task: str, files: list[str]) -> dict[str, Any]:
    runtime = load_runtime(root)
    if runtime and _approval_proof(root, runtime) is not None:
        current_files = set(_task_files(root, runtime))
        target = sorted(dict.fromkeys(str(item).strip() for item in files if str(item).strip()))
        selected = {
            path for path in current_files if any(_core()._inside(path, [candidate]) for candidate in target)
        }
        if current_files and selected == current_files:
            raise TideError(
                "split not required: the current fingerprint already has compatible approval; "
                "proceed to commit_check, or use reopen(code_change_required=true) before further edits"
            )
    return _ORIGINALS["split"](root, task=task, files=files)


def reopen(
    root: Path,
    *,
    reason: str,
    code_change_required: bool = False,
) -> dict[str, Any]:
    result = _ORIGINALS["reopen"](
        root,
        reason=reason,
        code_change_required=code_change_required,
    )
    if not code_change_required:
        return result
    runtime = load_runtime(root)
    hardgates = set(runtime.get("hardgates", []))
    authorized = set(runtime.get("authorized_hardgates", []))
    hardgates.discard(_BUDGET_GATE)
    authorized.discard(_BUDGET_GATE)
    runtime["hardgates"] = sorted(hardgates)
    runtime["authorized_hardgates"] = sorted(authorized & hardgates)
    runtime["split_required"] = False
    runtime["split_reasons"] = []
    runtime["extended_investigation_grant"] = None
    save_runtime(root, runtime)
    return _normalize_report(root, result, closure_check=False)


def authorize(
    root: Path,
    gates: list[str] | None = None,
    *,
    all_gates: bool = False,
) -> dict[str, Any]:
    before = load_runtime(root)
    code_reopen = isinstance(before.get("reopen_request"), dict)
    result = _ORIGINALS["authorize"](root, gates, all_gates=all_gates)
    if not code_reopen:
        return result
    runtime = load_runtime(root)
    if runtime.get("lifecycle") != "active" or runtime.get("reopen_request") is not None:
        return result
    metrics = runtime.setdefault("workflow_metrics", {})
    for key in (
        "review_cycles",
        "review_attempts",
        "review_cancelled",
        "review_packets",
        "scope_expansions",
        "validation_runs",
    ):
        metrics[key] = 0
    runtime["split_required"] = False
    runtime["split_reasons"] = []
    runtime["closure_warning"] = None
    save_runtime(root, runtime)
    return _ORIGINALS["preparation_report"](root, runtime)


def check(root: Path) -> dict[str, Any]:
    return _normalize_report(root, _ORIGINALS["check"](root), closure_check=True)


def preparation_report(root: Path, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    return _normalize_report(
        root,
        _ORIGINALS["preparation_report"](root, runtime),
        closure_check=False,
    )


def resume(root: Path) -> dict[str, Any]:
    hook = ensure_commit_hook(root)
    result = _normalize_report(root, _ORIGINALS["resume"](root), closure_check=False)
    if isinstance(result, dict):
        result["commit_hook"] = hook
    return result


def commit_check(root: Path) -> dict[str, Any]:
    result = _ORIGINALS["commit_check"](root)
    runtime = load_runtime(root)
    if not runtime or not isinstance(result, dict):
        return result
    proof = _approval_proof(root, runtime)
    result["approval_proof"] = proof
    if proof is None:
        return result

    quality = check(root)
    ignored = {
        _COMMIT_REVIEW_BLOCKER,
        _COMMIT_FINGERPRINT_BLOCKER,
        _BUDGET_BLOCKER,
        *_REVIEW_BLOCKERS,
    }
    blockers = [
        str(blocker)
        for blocker in result.get("blockers", [])
        if str(blocker) not in ignored
    ]
    for blocker in quality.get("blockers", []):
        text = str(blocker)
        if text and text not in blockers:
            blockers.append(text)
    blockers = list(dict.fromkeys(blockers))
    pending = list(quality.get("pending_hardgates", result.get("pending_hardgates", [])))
    check_ready = bool(quality.get("ready"))
    allowed = not blockers and check_ready and not pending
    result["blockers"] = blockers
    result["allowed"] = allowed
    result["review_id"] = proof.get("review_id")
    result["pending_hardgates"] = pending
    result["check_ready"] = check_ready
    result["agent_should_continue"] = not allowed and not bool(result.get("user_action_required"))
    if allowed:
        result["next_action"] = "commit may proceed; run tide check again after the commit"
    elif blockers:
        result["next_action"] = str(
            quality.get("next_action")
            or result.get("next_action")
            or "resolve the Tide blockers before committing"
        )
    return result
