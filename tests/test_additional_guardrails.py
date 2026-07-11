from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tide.artifacts import _tail
from tide.core import (
    authorize,
    check,
    create_review_packet,
    external_acknowledge,
    get_review_packet,
    prepare,
    record_validation,
    revise,
    submit_review,
)
from tide.project import TideError, load_runtime, save_runtime


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Tide Test")
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", "app.py")
    git(root, "commit", "-m", "init")
    return root


def test_external_change_can_be_acknowledged_without_joining_boundary(
    tmp_path: Path,
) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    (root / "session.md").write_text("external session\n", encoding="utf-8")

    blocked = check(root)
    assert blocked["outside_boundary"] == ["session.md"]

    result = external_acknowledge(
        root,
        ["session.md"],
        reason="session export created by the client",
    )
    assert result["outside_boundary"] == []
    ready = check(root)
    assert ready["ready"]
    assert ready["files"] == ["app.py"]
    assert ready["boundary"] == ["app.py"]
    assert ready["acknowledged_external_changes"][0]["file"] == "session.md"

    (root / "session.md").write_text("external session changed\n", encoding="utf-8")
    changed = check(root)
    assert not changed["ready"]
    assert changed["outside_boundary"] == ["session.md"]


def test_absorbing_changed_file_requires_scope_expansion_authorization(
    tmp_path: Path,
) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app", ["app.py"])
    (root / "other.py").write_text("OTHER = 1\n", encoding="utf-8")

    report = revise(root, add_files=["other.py"])
    assert "scope_expansion" in report["pending_hardgates"]
    assert report["scope_expansion_files"] == ["other.py"]
    assert not report["mutation_allowed"]

    report = authorize(root, gates=["scope_expansion"])
    assert report["mutation_allowed"]


def test_truncated_review_packet_cannot_be_approved(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    large = root / "large.txt"
    large.write_text("a" * 130_000 + "\n", encoding="utf-8")
    git(root, "add", "large.txt")
    git(root, "commit", "-m", "large")

    prepare(root, "change large file", ["large.txt"])
    large.write_text("b" * 130_000 + "\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    runtime = load_runtime(root)
    runtime["review_required"] = True
    save_runtime(root, runtime)

    meta = create_review_packet(root)
    assert meta["diff_truncated"]
    packet = get_review_packet(root, meta["review_id"])
    with pytest.raises(TideError, match="cannot approve a truncated review packet"):
        submit_review(
            root,
            review_id=meta["review_id"],
            submission_token=packet["submission_token"],
            approved=True,
            findings=[],
        )


def test_compact_tail_caps_lines_and_total_bytes() -> None:
    text = "\n".join("x" * 2_000 for _ in range(30))
    tail = _tail(text)
    assert tail
    assert all(len(line) <= 400 for line in tail)
    assert len("\n".join(tail).encode("utf-8")) <= 4096
