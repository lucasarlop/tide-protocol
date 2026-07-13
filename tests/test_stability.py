from __future__ import annotations

import subprocess
from pathlib import Path

from tide.core import (
    authorize,
    check,
    commit_check,
    create_review_packet,
    ensure_commit_hook,
    get_review_packet,
    prepare,
    record_validation,
    reopen,
    submit_review,
)
from tide.project import load_runtime, save_runtime


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )


def make_repo(tmp_path: Path, files: dict[str, str] | None = None) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Tide Test")
    for name, content in (files or {"app.py": "VALUE = 1\n"}).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "init")
    return root


def approve_current(root: Path, files: list[str]) -> None:
    record_validation(
        root,
        ["python", "-c", "assert True"],
        covers=files,
        phase="final",
    )
    summary = create_review_packet(root)
    packet = get_review_packet(root, str(summary["review_id"]))
    submit_review(
        root,
        review_id=str(summary["review_id"]),
        submission_token=str(packet["submission_token"]),
        approved=True,
        findings=[],
    )


def test_commit_check_allows_only_current_approved_staged_delta(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change local helper", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    approve_current(root, ["app.py"])
    git(root, "add", "app.py")

    report = commit_check(root)

    assert report["allowed"] is True
    assert report["blockers"] == []
    assert report["staged_files"] == ["app.py"]


def test_commit_check_blocks_edit_after_review(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change local helper", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    approve_current(root, ["app.py"])
    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    git(root, "add", "app.py")

    report = commit_check(root)

    assert report["allowed"] is False
    assert report["agent_should_continue"] is True
    assert any("fingerprint is not the approved fingerprint" in item for item in report["blockers"])


def test_commit_check_rejects_partial_or_outside_staging(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {
            "app.py": "A = 1\n",
            "ui.ts": "export const x = 1;\n",
            "note.md": "x\n",
        },
    )
    prepare(root, "change app and ui", ["app.py", "ui.ts"])
    (root / "app.py").write_text("A = 2\n", encoding="utf-8")
    (root / "ui.ts").write_text("export const x = 2;\n", encoding="utf-8")
    approve_current(root, ["app.py", "ui.ts"])
    (root / "note.md").write_text("y\n", encoding="utf-8")
    git(root, "add", "app.py", "note.md")

    report = commit_check(root)

    assert report["allowed"] is False
    assert report["outside_staged_files"] == ["note.md"]
    assert report["unstaged_task_files"] == ["ui.ts"]


def test_code_reopen_requires_gate_then_unlocks_new_review_cycle(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change local helper", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    approve_current(root, ["app.py"])
    runtime = load_runtime(root)
    runtime["workflow_metrics"]["scope_expansions"] = 9
    runtime["workflow_metrics"]["validation_runs"] = 17
    save_runtime(root, runtime)

    pending = reopen(
        root,
        reason="approved UI still has a verified clipping defect",
        code_change_required=True,
    )

    assert pending["lifecycle"] == "reopen_pending"
    assert pending["pending_hardgates"] == ["closure_reopen"]
    assert pending["mutation_allowed"] is False

    reopened = authorize(root, gates=["closure_reopen"])
    runtime = load_runtime(root)

    assert reopened["lifecycle"] == "active"
    assert runtime["review"] is None
    assert runtime["approved_fingerprint"] is None
    assert runtime["closure_locked"] is False
    assert "closure_reopen" not in runtime["hardgates"]
    assert runtime["workflow_metrics"]["scope_expansions"] == 0
    assert runtime["workflow_metrics"]["validation_runs"] == 0


def test_default_reopen_keeps_unchanged_approved_code_operational(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change local helper", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    approve_current(root, ["app.py"])

    report = reopen(root, reason="verify the approved runtime")

    assert report["lifecycle"] == "operational_verification"
    assert report["closure_locked"] is True


def test_approved_fingerprint_is_not_blocked_by_real_review_budget(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change local helper", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    approve_current(root, ["app.py"])
    runtime = load_runtime(root)
    runtime["workflow_metrics"]["review_cycles"] = 99
    runtime["workflow_metrics"]["review_attempts"] = 99
    runtime["hardgates"] = sorted(
        set(runtime.get("hardgates", [])) | {"extended_investigation"}
    )
    runtime["split_required"] = True
    runtime["split_reasons"] = ["review attempt budget exceeded"]
    save_runtime(root, runtime)

    report = check(root)

    assert "extended_investigation" not in report["pending_hardgates"]
    assert "task must be split or extended investigation explicitly authorized" not in report["blockers"]
    assert report["split_required"] is False
    assert report["ready"] is True


def test_commit_hook_is_managed_and_preserves_existing_shell_hook(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    hooks = Path(git(root, "rev-parse", "--git-path", "hooks").stdout.strip())
    if not hooks.is_absolute():
        hooks = root / hooks
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\necho existing\n", encoding="utf-8")

    result = ensure_commit_hook(root)
    text = hook.read_text(encoding="utf-8")

    assert result["installed"] is True
    assert "tide commit-check --hook" in text
    assert "echo existing" in text
    assert text.count("# tide:commit-gate:start") == 1
    assert hook.stat().st_mode & 0o111


def test_managed_hook_blocks_real_commit_until_new_fingerprint_is_approved(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    ensure_commit_hook(root)
    prepare(root, "change local helper", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    approve_current(root, ["app.py"])
    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    git(root, "add", "app.py")

    blocked = git(root, "commit", "-m", "must not commit", check=False)

    assert blocked.returncode != 0
    assert "Tide blocked this commit" in blocked.stderr
    assert git(root, "rev-parse", "--short", "HEAD").stdout.strip() != ""

    approve_current(root, ["app.py"])
    git(root, "add", "app.py")
    committed = git(root, "commit", "-m", "approved change", check=False)

    assert committed.returncode == 0, committed.stderr
    report = check(root)
    assert report["lifecycle"] == "committed"
    assert report["ready"] is True
