from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tide.core import (
    authorize,
    check,
    create_review_packet,
    get_review_packet,
    handoff,
    prepare,
    record_validation,
    split,
    submit_review,
)
from tide.project import TideError, load_runtime, save_runtime


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
    git(root, "add", "app.py", "helper.py")
    git(root, "commit", "-m", "init")
    return root


def test_split_resets_child_budget_and_preserves_compatible_evidence(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "large database change", ["app.py", "helper.py"])
    authorize(root, all_gates=True)
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    record_validation(
        root,
        [sys.executable, "-c", "assert True"],
        covers=["app.py"],
    )
    runtime = load_runtime(root)
    runtime["workflow_metrics"].update(
        {
            "review_cycles": 7,
            "review_attempts": 9,
            "scope_expansions": 5,
            "validation_runs": 12,
        }
    )
    save_runtime(root, runtime)

    report = split(root, task="finish app child", files=["app.py"])

    assert report["boundary"] == ["app.py"]
    assert report["segment_index"] == 1
    assert report["segment_history_count"] == 1
    assert report["workflow_metrics"]["review_cycles"] == 0
    assert report["workflow_metrics"]["review_attempts"] == 0
    assert not report["split_required"]
    assert check(root)["current_validation_count"] == 1


def test_pending_packet_is_reused_and_repeated_reads_count_attempts(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app and helper", ["app.py", "helper.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    record_validation(root, [sys.executable, "-c", "assert True"])

    first = create_review_packet(root)
    second = create_review_packet(root)
    assert second["review_id"] == first["review_id"]
    assert second["reused"] is True

    get_review_packet(root, first["review_id"])
    get_review_packet(root, first["review_id"])
    runtime = load_runtime(root)
    assert runtime["workflow_metrics"]["review_attempts"] == 2
    assert runtime["workflow_metrics"]["review_cancelled"] == 1


def test_full_review_after_baseline_requires_central_reason(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app and helper", ["app.py", "helper.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    record_validation(root, [sys.executable, "-c", "assert True"])
    meta = create_review_packet(root)
    packet = get_review_packet(root, meta["review_id"])
    submit_review(
        root,
        review_id=meta["review_id"],
        submission_token=packet["submission_token"],
        approved=False,
        findings=[{"id": "needs-fix", "severity": "blocking", "message": "needs fix"}],
    )

    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    record_validation(
        root,
        [sys.executable, "-c", "assert True"],
        covers=["app.py", "helper.py"],
    )

    with pytest.raises(TideError, match="requires full_reason"):
        create_review_packet(root, full=True)
    with pytest.raises(TideError, match="architecture"):
        create_review_packet(root, full=True, full_reason="routine retry")

    allowed = create_review_packet(
        root,
        full=True,
        full_reason="central architecture invariant changed",
    )
    assert allowed["review_mode"] == "full"


def test_check_and_handoff_expose_exact_next_action(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "database migration", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    report = check(root)
    assert report["primary_blocker"]
    assert "database" in report["pending_hardgates"]
    assert "authorize pending hardgates" in report["next_action"]

    checkpoint = handoff(root)
    assert checkpoint["pending_hardgates"]
    assert checkpoint["next_action"]
    assert len(str(checkpoint)) < 5000


def test_extended_investigation_grant_limits_new_review_packets(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "database migration", ["app.py", "helper.py"])
    authorize(root, all_gates=True)
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    record_validation(root, [sys.executable, "-c", "assert True"])
    runtime = load_runtime(root)
    runtime["workflow_metrics"]["review_cycles"] = 4
    save_runtime(root, runtime)

    authorize(root, gates=["extended_investigation"])
    first = create_review_packet(root)
    packet = get_review_packet(root, first["review_id"])
    submit_review(
        root,
        review_id=first["review_id"],
        submission_token=packet["submission_token"],
        approved=False,
        findings=[{"id": "block-one", "severity": "blocking", "message": "block one"}],
    )
    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    record_validation(
        root,
        [sys.executable, "-c", "assert True"],
        covers=["app.py", "helper.py"],
    )
    second = create_review_packet(root)
    packet = get_review_packet(root, second["review_id"])
    submit_review(
        root,
        review_id=second["review_id"],
        submission_token=packet["submission_token"],
        approved=False,
        findings=[{"id": "block-two", "severity": "blocking", "message": "block two"}],
    )
    (root / "app.py").write_text("VALUE = 4\n", encoding="utf-8")
    record_validation(
        root,
        [sys.executable, "-c", "assert True"],
        covers=["app.py", "helper.py"],
    )

    with pytest.raises(TideError, match="allowance expired"):
        create_review_packet(root)
