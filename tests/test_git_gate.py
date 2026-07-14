from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tide.core import (
    check,
    commit_check,
    create_review_packet,
    ensure_commit_hook,
    get_review_packet,
    prepare,
    record_validation,
    submit_review,
)


def approve(repo: Path, files: list[str]) -> None:
    record_validation(repo, [sys.executable, "-c", "assert True"], covers=files, phase="final")
    summary = create_review_packet(repo)
    packet = get_review_packet(repo, summary["review_id"])
    submit_review(repo, review_id=summary["review_id"], submission_token=packet["submission_token"], approved=True, findings=[])


def test_commit_check_requires_exact_staging(repo: Path) -> None:
    prepare(repo, "change two files", ["app.py", "helper.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    approve(repo, ["app.py", "helper.py"])
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    report = commit_check(repo)
    assert report["allowed"] is False
    assert report["unstaged_task_files"] == ["helper.py"]


def test_commit_check_allows_approved_exact_delta(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    approve(repo, ["app.py"])
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    assert commit_check(repo)["allowed"] is True


def test_edit_after_review_blocks_commit(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    approve(repo, ["app.py"])
    (repo / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    assert commit_check(repo)["allowed"] is False


def test_managed_hook_blocks_real_unapproved_commit(repo: Path) -> None:
    ensure_commit_hook(repo)
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    result = subprocess.run(["git", "commit", "-m", "blocked"], cwd=repo, text=True, capture_output=True)
    assert result.returncode != 0
    assert "Tide blocked this commit" in result.stderr


def test_post_commit_check_marks_task_committed(repo: Path) -> None:
    ensure_commit_hook(repo)
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    approve(repo, ["app.py"])
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "approved"], cwd=repo, check=True, capture_output=True)
    report = check(repo)
    assert report["lifecycle"] == "committed"
    assert report["ready"] is True
