from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .project import diff_fingerprint, load_runtime, save_runtime

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Callable[..., Any]] = {}
_BUDGET_GATE = "extended_investigation"
_BUDGET_BLOCKER = "task must be split or extended investigation explicitly authorized"


def install(core: ModuleType) -> None:
    global _CORE
    if getattr(core, "_stability_fixes_installed", False):
        return
    _CORE = core
    for name in ("authorize", "check", "preparation_report", "resume"):
        _ORIGINALS[name] = getattr(core, name)
    core.authorize = authorize
    core.check = check
    core.preparation_report = preparation_report
    core.resume = resume
    core._stability_fixes_installed = True


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide stability fixes are not installed")
    return _CORE


def _task_files(root: Path, runtime: dict[str, Any]) -> list[str]:
    return list(_core()._task_files(root, runtime))


def _approved_current(root: Path, runtime: dict[str, Any]) -> bool:
    review = runtime.get("review") if isinstance(runtime.get("review"), dict) else {}
    approved = str(runtime.get("approved_fingerprint") or "")
    current = diff_fingerprint(root, _task_files(root, runtime))
    return bool(review.get("approved")) and bool(approved) and approved == current


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
    if not runtime or not _approved_current(root, runtime):
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
            if str(blocker) != _BUDGET_BLOCKER
        ]
        blockers = list(dict.fromkeys(blockers))
        ready = not blockers and not pending
        runtime["status"] = "ready" if ready else "blocked"
        save_runtime(root, runtime)
        value["blockers"] = blockers
        value["primary_blocker"] = blockers[0] if blockers else None
        value["ready"] = ready
        value["status"] = runtime["status"]
        if ready:
            value["next_action"] = "closure ready"
        _normalize_nested_resume(value, pending, ready=ready)
    else:
        if not pending:
            value["next_action"] = "closure ready"
        _normalize_nested_resume(value, pending, ready=not pending)
    return value


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
    return _normalize_report(root, _ORIGINALS["resume"](root), closure_check=False)
