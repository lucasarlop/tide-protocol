from __future__ import annotations

import subprocess
from pathlib import Path

from tide.core import (
    create_review_packet,
    get_review_packet,
    prepare,
    record_validation,
    revise,
    split,
    start_validation,
    submit_review,
    validation_log,
    validation_wait,
)
from tide.project import load_runtime
from tide.session_stability import command_covers


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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
    (root / "ui.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "note.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tests/unit").mkdir(parents=True)
    (root / "tests/unit/test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
    (root / "scripts").mkdir()
    runner = root / "scripts/run_tests.sh"
    runner.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    runner.chmod(0o755)

    git(root, "add", ".")
    git(root, "commit", "-m", "init")
    return root


def test_broader_directory_validation_covers_narrow_required_command() -> None:
    assert command_covers(
        ["./scripts/run_tests.sh", "tests/unit/"],
        "./scripts/run_tests.sh tests/unit/test_app.py",
    )
    assert not command_covers(
        ["./scripts/run_tests.sh", "tests/integration/"],
        "./scripts/run_tests.sh tests/unit/test_app.py",
    )


def test_revise_prunes_narrow_validation_when_broader_suite_is_added(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    narrow = "./scripts/run_tests.sh tests/unit/test_app.py"
    broad = "./scripts/run_tests.sh tests/unit/"
    prepare(root, "change helper", ["app.py"], [narrow])

    revise(root, add_required_validations=[broad])

    runtime = load_runtime(root)
    assert runtime["required_validations"] == [broad]


def test_broad_passing_command_satisfies_narrow_mandatory_validation(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    narrow = "./scripts/run_tests.sh tests/unit/test_app.py"
    prepare(root, "change helper", ["app.py"], [narrow])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    record_validation(
        root,
        ["./scripts/run_tests.sh", "tests/unit/"],
        covers=["app.py"],
        phase="final",
    )
    packet = create_review_packet(root)

    assert packet["review_id"]
    assert packet["reviewer_submits_verdict"] is True
    assert packet["writer_must_not_resubmit"] is True


def test_split_inherits_current_parent_validation_for_child_files(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change three files", ["app.py", "ui.py", "note.py"])
    for name in ("app.py", "ui.py", "note.py"):
        (root / name).write_text("VALUE = 2\n", encoding="utf-8")

    record_validation(
        root,
        ["python", "-c", "assert True"],
        covers=["app.py", "ui.py", "note.py"],
        phase="final",
    )

    report = split(root, task="finish app and ui", files=["app.py", "ui.py"])
    runtime = load_runtime(root)

    assert report["inherited_validation_count"] == 1
    assert len(runtime["validations"]) == 1
    assert runtime["validations"][0]["files"] == ["app.py", "ui.py"]
    assert runtime["validations"][0]["inherited_from_parent_segment"] is True


def test_validation_wait_returns_log_and_failure_summary(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "break helper", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    started = start_validation(
        root,
        [
            "python",
            "-c",
            "import sys; print('FAILED test_demo'); raise AssertionError('boom')",
        ],
        covers=["app.py"],
        phase="targeted",
    )
    result = validation_wait(root, str(started["validation_id"]), wait_seconds=20)

    assert result["status"] == "completed"
    assert result["passed"] is False
    assert result["log_id"].startswith("validation-")
    assert result["failure_summary"]
    assert result["agent_should_continue"] is True
    assert result["user_action_required"] is False

    by_job_id = validation_log(root, str(started["validation_id"]))
    assert by_job_id["log_id"] == result["log_id"]
    assert "AssertionError" in by_job_id["content"]


def test_duplicate_review_submission_is_idempotent(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change helper", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(
        root,
        ["python", "-c", "assert True"],
        covers=["app.py"],
        phase="final",
    )
    summary = create_review_packet(root)
    packet = get_review_packet(root, str(summary["review_id"]))
    arguments = {
        "review_id": str(summary["review_id"]),
        "submission_token": str(packet["submission_token"]),
        "approved": False,
        "findings": [
            {
                "id": "demo-blocker",
                "severity": "blocking",
                "message": "Fix the demo blocker.",
                "paths": ["app.py:1"],
                "expected_action": "Correct VALUE.",
            }
        ],
    }

    first = submit_review(root, **arguments)
    second = submit_review(root, **arguments)

    assert first["verdict_submitted"] is True
    assert first["idempotent"] is False
    assert second["verdict_submitted"] is True
    assert second["idempotent"] is True
    assert second["receipt_id"] == first["receipt_id"]
