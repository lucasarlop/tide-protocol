from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tide.core import (
    check,
    create_review_packet,
    get_review_packet,
    handoff,
    operational_verify,
    prepare,
    record_validation,
    reopen,
    resume,
    split,
    submit_review,
)
from tide.project import TideError, load_runtime


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Tide Test")
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 1\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "init")
    return root


def approve(root: Path, findings: list[dict] | None = None, approved: bool = True) -> dict:
    record_validation(
        root,
        [sys.executable, "-c", "assert True"],
        covers=["app.py", "helper.py"],
        phase="final",
    )
    meta = create_review_packet(root)
    packet = get_review_packet(root, meta["review_id"])
    return submit_review(
        root,
        review_id=meta["review_id"],
        submission_token=packet["submission_token"],
        approved=approved,
        findings=findings or [],
    )


def test_final_validation_is_reused_for_same_fingerprint(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    command = [sys.executable, "-c", "assert True"]

    first = record_validation(root, command, covers=["app.py"], phase="final")
    second = record_validation(root, command, covers=["app.py"], phase="final")

    assert first["passed"] is True
    assert second["passed"] is True
    assert second["reused"] is True
    assert len(load_runtime(root)["validations"]) == 1


def test_approved_fingerprint_cannot_be_reviewed_again(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app and helper", ["app.py", "helper.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    approve(root)

    with pytest.raises(TideError, match="already approved"):
        create_review_packet(root, full=True, full_reason="architecture changed")


def test_reopen_without_code_change_enters_operational_verification(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app and helper", ["app.py", "helper.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    approve(root)

    report = reopen(root, reason="rebuild local containers")
    assert report["lifecycle"] == "operational_verification"
    assert report["closure_locked"] is True

    verification = operational_verify(root, name="health", passed=True, details="HTTP 200")
    assert verification["passed"] is True
    assert load_runtime(root)["review"]["approved"] is True


def test_split_creates_parent_receipt_and_hides_parent_files(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app and helper", ["app.py", "helper.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    approve(root)

    report = split(root, task="finish app only", files=["app.py"])

    assert report["segment_receipt_count"] == 1
    closure = check(root)
    assert "helper.py" not in closure.get("outside_boundary", [])


def test_handoff_and_resume_are_compact_and_equivalent(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    first = handoff(root)
    second = resume(root)

    assert first["task"] == second["task"]
    assert first["segment_id"] == second["segment_id"]
    assert len(str(first)) < 2_000


def test_commit_matching_approved_files_closes_without_new_review(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app and helper", ["app.py", "helper.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    approve(root)

    git(root, "add", "app.py", "helper.py")
    git(root, "commit", "-m", "change approved files")
    report = check(root)

    assert report["ready"] is True
    assert report["lifecycle"] == "committed"
    assert report["primary_blocker"] is None


def test_review_keeps_paths_and_expected_action(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app and helper", ["app.py", "helper.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    review = approve(
        root,
        approved=False,
        findings=[
            {
                "id": "app-value",
                "severity": "blocking",
                "message": "app value incomplete",
                "paths": ["app.py:1"],
                "expected_action": "set the final value",
            }
        ],
    )

    finding = review["findings"][0]
    assert finding["paths"] == ["app.py:1"]
    assert finding["expected_action"] == "set the final value"
