from __future__ import annotations

import stat
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from .project import (
    TideError,
    diff_fingerprint,
    load_runtime,
    run_git,
    save_runtime,
    staged_files,
)

_CORE: ModuleType | None = None
_ORIGINALS: dict[str, Callable[..., Any]] = {}

_HOOK_START = "# tide:commit-gate:start"
_HOOK_END = "# tide:commit-gate:end"
_HOOK_BLOCK = f"""{_HOOK_START}
if command -v tide >/dev/null 2>&1; then
  tide commit-check --hook || exit $?
fi
{_HOOK_END}"""
_BUDGET_GATE = "extended_investigation"
_REOPEN_GATE = "closure_reopen"


def install(core: ModuleType) -> None:
    global _CORE
    if getattr(core, "_stability_controls_installed", False):
        return
    _CORE = core
    for name in ("reopen", "authorize", "check", "preparation_report", "resume"):
        _ORIGINALS[name] = getattr(core, name)
    core.reopen = reopen
    core.authorize = authorize
    core.check = check
    core.preparation_report = preparation_report
    core.resume = resume
    core.commit_check = commit_check
    core.ensure_commit_hook = ensure_commit_hook
    core._stability_controls_installed = True


def _core() -> ModuleType:
    if _CORE is None:
        raise RuntimeError("Tide stability controls are not installed")
    return _CORE


def _task_files(root: Path, runtime: dict[str, Any]) -> list[str]:
    return list(_core()._task_files(root, runtime))


def _current_fingerprint(root: Path, runtime: dict[str, Any]) -> str:
    return diff_fingerprint(root, _task_files(root, runtime))


def _approved_current(root: Path, runtime: dict[str, Any]) -> bool:
    review = runtime.get("review") if isinstance(runtime.get("review"), dict) else {}
    approved = str(runtime.get("approved_fingerprint") or "")
    return bool(review.get("approved")) and bool(approved) and approved == _current_fingerprint(root, runtime)


def _clear_approved_budget_gate(root: Path, runtime: dict[str, Any]) -> bool:
    if not _approved_current(root, runtime):
        return False
    changed = False
    hardgates = set(runtime.get("hardgates", []))
    authorized = set(runtime.get("authorized_hardgates", []))
    if _BUDGET_GATE in hardgates or _BUDGET_GATE in authorized:
        hardgates.discard(_BUDGET_GATE)
        authorized.discard(_BUDGET_GATE)
        changed = True
    if runtime.get("split_required"):
        runtime["split_required"] = False
        runtime["split_reasons"] = []
        changed = True
    if runtime.get("extended_investigation_grant") is not None:
        runtime["extended_investigation_grant"] = None
        changed = True
    if changed:
        runtime["hardgates"] = sorted(hardgates)
        runtime["authorized_hardgates"] = sorted(authorized & hardgates)
        save_runtime(root, runtime)
    return changed


def _archive_review(runtime: dict[str, Any]) -> None:
    review = runtime.get("review")
    if not isinstance(review, dict) or not review.get("review_id"):
        return
    history = runtime.setdefault("review_history", [])
    if not any(
        isinstance(item, dict) and item.get("review_id") == review.get("review_id")
        for item in history
    ):
        history.append(dict(review))


def reopen(
    root: Path,
    *,
    reason: str,
    code_change_required: bool = False,
) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime:
        raise TideError("run tide prepare before reopen")
    reason = reason.strip()
    if not reason:
        raise TideError("reopen requires a concrete blocking reason")
    if not code_change_required or not runtime.get("approved_fingerprint"):
        return _ORIGINALS["reopen"](root, reason=reason)

    hardgates = set(runtime.get("hardgates", []))
    authorized = set(runtime.get("authorized_hardgates", []))
    hardgates.add(_REOPEN_GATE)
    authorized.discard(_REOPEN_GATE)
    runtime["hardgates"] = sorted(hardgates)
    runtime["authorized_hardgates"] = sorted(authorized & hardgates)
    runtime["reopen_request"] = {
        "reason": reason,
        "code_change_required": True,
    }
    runtime["closure_reason"] = reason
    runtime["closure_locked"] = True
    runtime["lifecycle"] = "reopen_pending"
    runtime["status"] = "blocked"
    save_runtime(root, runtime)
    return _ORIGINALS["preparation_report"](root, runtime)


def _finalize_code_reopen(root: Path, runtime: dict[str, Any]) -> dict[str, Any]:
    _archive_review(runtime)
    hardgates = set(runtime.get("hardgates", [])) - {_REOPEN_GATE, _BUDGET_GATE}
    authorized = set(runtime.get("authorized_hardgates", [])) - {_REOPEN_GATE, _BUDGET_GATE}
    runtime["hardgates"] = sorted(hardgates)
    runtime["authorized_hardgates"] = sorted(authorized & hardgates)
    runtime["review"] = None
    runtime["pending_review"] = None
    runtime["approved_fingerprint"] = None
    runtime["approved_files"] = {}
    runtime["approved_content"] = {}
    runtime["approved_at"] = None
    runtime["committed_sha"] = None
    runtime["closure_locked"] = False
    runtime["closure_reason"] = str(
        (runtime.get("reopen_request") or {}).get("reason") or runtime.get("closure_reason") or ""
    )
    runtime["reopen_request"] = None
    runtime["lifecycle"] = "active"
    runtime["status"] = "revising"
    runtime["split_required"] = False
    runtime["split_reasons"] = []
    runtime["extended_investigation_grant"] = None
    metrics = runtime.setdefault("workflow_metrics", {})
    metrics["reopens"] = int(metrics.get("reopens", 0)) + 1
    for key in ("review_cycles", "review_attempts", "review_cancelled", "review_packets"):
        metrics[key] = 0
    save_runtime(root, runtime)
    return _ORIGINALS["preparation_report"](root, runtime)


def authorize(
    root: Path,
    gates: list[str] | None = None,
    *,
    all_gates: bool = False,
) -> dict[str, Any]:
    requested = set(gates or [])
    runtime_before = load_runtime(root)
    if all_gates:
        requested = set(runtime_before.get("hardgates", []))
    _ORIGINALS["authorize"](root, gates, all_gates=all_gates)
    runtime = load_runtime(root)
    if _REOPEN_GATE in requested and _REOPEN_GATE in set(runtime.get("authorized_hardgates", [])):
        return _finalize_code_reopen(root, runtime)
    return _ORIGINALS["preparation_report"](root, runtime)


def _prepare_closure_state(root: Path) -> None:
    runtime = load_runtime(root)
    if runtime:
        _clear_approved_budget_gate(root, runtime)


def check(root: Path) -> dict[str, Any]:
    _prepare_closure_state(root)
    return _ORIGINALS["check"](root)


def preparation_report(root: Path, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    current = runtime or load_runtime(root)
    if current:
        _clear_approved_budget_gate(root, current)
        current = load_runtime(root)
    return _ORIGINALS["preparation_report"](root, current)


def resume(root: Path) -> dict[str, Any]:
    _prepare_closure_state(root)
    return _ORIGINALS["resume"](root)


def _authorization_request(pending: list[str]) -> dict[str, Any] | None:
    if not pending:
        return None
    return {
        "tool": "authorize",
        "arguments": {"gates": pending, "all": False},
        "interaction": "client_permission_prompt",
        "message": "Authorize the pending Tide hardgates.",
    }


def commit_check(root: Path) -> dict[str, Any]:
    runtime = load_runtime(root)
    if not runtime or not runtime.get("task"):
        return {
            "allowed": True,
            "active_task": False,
            "blockers": [],
            "next_action": "commit may proceed; no active Tide task",
            "user_action_required": False,
            "agent_should_continue": False,
            "authorization_request": None,
        }

    _clear_approved_budget_gate(root, runtime)
    runtime = load_runtime(root)
    report = check(root)
    runtime = load_runtime(root)
    task_files = _task_files(root, runtime)
    staged = staged_files(root)
    task_set = set(task_files)
    staged_set = set(staged)
    current_fingerprint = _current_fingerprint(root, runtime)
    approved_fingerprint = str(runtime.get("approved_fingerprint") or "")
    review = runtime.get("review") if isinstance(runtime.get("review"), dict) else {}
    pending = sorted(
        set(runtime.get("hardgates", [])) - set(runtime.get("authorized_hardgates", []))
    )

    blockers: list[str] = []
    if not review.get("approved"):
        blockers.append("current task has no approved independent review")
    if not approved_fingerprint or approved_fingerprint != current_fingerprint:
        blockers.append("current worktree fingerprint is not the approved fingerprint")
    for blocker in report.get("blockers", []):
        text = str(blocker)
        if text and text not in blockers:
            blockers.append(text)
    if not staged:
        blockers.append("no task files are staged")
    outside = sorted(staged_set - task_set)
    missing = sorted(task_set - staged_set)
    if outside:
        blockers.append("staged files outside the current Tide delta: " + ", ".join(outside))
    if missing:
        blockers.append("changed Tide files are not staged: " + ", ".join(missing))

    blockers = list(dict.fromkeys(blockers))
    allowed = not blockers and bool(report.get("ready")) and not pending
    user_action_required = bool(pending)
    if allowed:
        next_action = "commit may proceed; run tide check again after the commit"
    elif pending:
        next_action = "call authorize with the pending hardgates; let the client request user approval"
    elif approved_fingerprint != current_fingerprint or not review.get("approved"):
        next_action = "complete current validation and independent review before committing"
    elif outside or missing:
        next_action = "stage exactly the changed files in the current Tide task"
    else:
        next_action = str(report.get("next_action") or "resolve the Tide blockers before committing")

    return {
        "allowed": allowed,
        "active_task": True,
        "blockers": blockers,
        "task_files": task_files,
        "staged_files": staged,
        "outside_staged_files": outside,
        "unstaged_task_files": missing,
        "current_fingerprint": current_fingerprint,
        "approved_fingerprint": approved_fingerprint or None,
        "review_id": review.get("review_id"),
        "pending_hardgates": pending,
        "check_ready": bool(report.get("ready")),
        "next_action": next_action,
        "user_action_required": user_action_required,
        "agent_should_continue": not allowed and not user_action_required,
        "authorization_request": _authorization_request(pending),
    }


def _hooks_dir(root: Path) -> Path:
    result = run_git(["rev-parse", "--git-path", "hooks"], cwd=root)
    value = Path(result.stdout.strip())
    return value if value.is_absolute() else (root / value).resolve()


def _replace_managed_block(text: str) -> str:
    if _HOOK_START not in text or _HOOK_END not in text:
        return text
    prefix, tail = text.split(_HOOK_START, 1)
    _, suffix = tail.split(_HOOK_END, 1)
    return prefix.rstrip() + "\n" + suffix.lstrip("\n")


def ensure_commit_hook(root: Path) -> dict[str, Any]:
    path = _hooks_dir(root) / "pre-commit"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        return {
            "installed": False,
            "path": str(path),
            "warning": "existing pre-commit hook is a symlink; Tide did not modify it",
        }

    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current and not current.startswith("#!"):
        return {
            "installed": False,
            "path": str(path),
            "warning": "existing pre-commit hook has no shell shebang; Tide did not modify it",
        }
    if current:
        shebang = current.splitlines()[0]
        if not any(shell in shebang for shell in ("sh", "bash", "zsh", "dash")):
            return {
                "installed": False,
                "path": str(path),
                "warning": "existing pre-commit hook is not a supported shell script",
            }
        unmanaged = _replace_managed_block(current)
        lines = unmanaged.splitlines()
        updated = "\n".join([lines[0], _HOOK_BLOCK, *lines[1:]]).rstrip() + "\n"
    else:
        updated = "#!/bin/sh\n" + _HOOK_BLOCK + "\n"

    path.write_text(updated, encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {
        "installed": True,
        "path": str(path),
        "managed": True,
    }
