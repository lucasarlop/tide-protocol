from __future__ import annotations

import stat
from pathlib import Path
from typing import Any

from .evidence import approval_proof
from .project import load_runtime, run_git, staged_files

_HOOK_START = "# tide:commit-gate:start"
_HOOK_END = "# tide:commit-gate:end"
_HOOK_BLOCK = f"""{_HOOK_START}
if command -v tide >/dev/null 2>&1; then
  tide commit-check --hook || exit $?
fi
{_HOOK_END}"""


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

    changed = updated != current
    if changed:
        path.write_text(updated, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {"installed": True, "changed": changed, "path": str(path)}


def commit_check(root: Path, evaluation: dict[str, Any], task_files: list[str]) -> dict[str, Any]:
    state = load_runtime(root)
    if not state:
        return {
            "allowed": True,
            "active_task": False,
            "blockers": [],
            "next_action": "commit may proceed; no active Tide task",
            "user_action_required": False,
            "agent_should_continue": False,
            "authorization_request": None,
        }

    staged = staged_files(root)
    task_set = set(task_files)
    staged_set = set(staged)
    proof = approval_proof(root, state, task_files)
    blockers: list[str] = []

    if proof is None:
        blockers.append("current worktree fingerprint has no compatible approval proof")
    for blocker in evaluation.get("blockers", []):
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
    user_action_required = bool(evaluation.get("user_action_required"))
    allowed = not blockers and bool(evaluation.get("ready")) and not user_action_required
    if allowed:
        next_action = "commit may proceed; run tide check again after the commit"
    elif user_action_required:
        next_action = str(evaluation.get("next_action") or "resolve the pending user decision")
    elif outside or missing:
        next_action = "stage exactly the changed files in the current Tide task"
    else:
        next_action = str(evaluation.get("next_action") or "resolve the Tide blockers before committing")

    return {
        "allowed": allowed,
        "active_task": True,
        "blockers": blockers,
        "task_files": task_files,
        "staged_files": staged,
        "outside_staged_files": outside,
        "unstaged_task_files": missing,
        "approval_proof": proof,
        "review_id": proof.get("review_id") if proof else None,
        "check_ready": bool(evaluation.get("ready")),
        "next_action": next_action,
        "user_action_required": user_action_required,
        "agent_should_continue": not allowed and not user_action_required,
        "authorization_request": evaluation.get("authorization_request"),
        "decision_request": evaluation.get("decision_request"),
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
