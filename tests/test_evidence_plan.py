from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

from tide.core import (
    check,
    create_review_packet,
    get_review_packet,
    prepare,
    record_validation,
    revise,
    review_packet,
    start_validation,
    submit_review,
    validation_status,
)
from tide.project import TideError


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


def make_repo(tmp_path: Path, app_text: str = "VALUE = 1\n") -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Tide Test")
    (root / "app.py").write_text(app_text, encoding="utf-8")
    git(root, "add", "app.py")
    git(root, "commit", "-m", "init")
    return root


def test_task_validation_plan_blocks_until_exact_command_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    required = f'{sys.executable} -c assert True'
    report = prepare(
        root,
        "change value",
        ["app.py"],
        required_validations=[required],
    )
    assert report["required_validations"] == [required]

    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, [sys.executable, "-c", "assert 1 + 1 == 2"])
    blocked = check(root)
    assert not blocked["ready"]
    assert blocked["missing_validations"] == [required]
    assert "required validations are missing for their covered files" in blocked["blockers"]

    record_validation(root, [sys.executable, "-c", "assert True"])
    assert check(root)["ready"]


def test_revise_can_change_validation_plan_and_invalidates_evidence(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    first = f'{sys.executable} -c assert True'
    second = f'{sys.executable} -c assert 2 + 2 == 4'
    prepare(root, "change value", ["app.py"], required_validations=[first])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, [sys.executable, "-c", "assert True"])
    assert check(root)["ready"]

    revised = revise(
        root,
        add_required_validations=[second],
        remove_required_validations=[first],
    )
    assert revised["revision"] == 1
    assert revised["required_validations"] == [second]
    blocked = check(root)
    assert not blocked["ready"]
    assert blocked["current_validation_count"] == 0


def test_background_validation_records_result_for_starting_fingerprint(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    required = f'{sys.executable} -c print("ok")'
    prepare(root, "change value", ["app.py"], required_validations=[required])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    started = start_validation(root, [sys.executable, "-c", 'print("ok")'], timeout=30)
    validation_id = str(started["validation_id"])
    result = started
    deadline = time.monotonic() + 10
    while result.get("status") != "completed" and time.monotonic() < deadline:
        time.sleep(0.05)
        result = validation_status(root, validation_id)

    assert result["status"] == "completed"
    assert result["passed"] is True
    assert result["recorded"] is True
    assert check(root)["ready"]


def test_reviewer_submits_bound_verdict_with_one_time_token(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change across files", ["app.py", "a.py", "b.py", "c.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, [sys.executable, "-c", "assert True"])

    summary = create_review_packet(root)
    packet = get_review_packet(root, str(summary["review_id"]))
    token = str(packet["submission_token"])

    with pytest.raises(TideError, match="invalid review submission token"):
        submit_review(
            root,
            review_id=str(summary["review_id"]),
            submission_token="wrong-token",
            approved=True,
            findings=[],
        )

    review = submit_review(
        root,
        review_id=str(summary["review_id"]),
        submission_token=token,
        approved=True,
        findings=["INFO: reviewed"],
    )
    assert review["receipt_id"].startswith("review-receipt-")
    assert check(root)["ready"]

    with pytest.raises(TideError, match="already has a submitted verdict"):
        submit_review(
            root,
            review_id=str(summary["review_id"]),
            submission_token=token,
            approved=True,
            findings=[],
        )


def test_simplicity_focus_ignores_unchanged_preexisting_long_function(tmp_path: Path) -> None:
    body = "def long_function():\n" + "".join("    pass\n" for _ in range(110))
    root = make_repo(tmp_path, body)
    prepare(root, "small edit", ["app.py"])
    (root / "app.py").write_text(body.replace("    pass\n", "    x = 1\n", 1), encoding="utf-8")
    record_validation(root, [sys.executable, "-c", "assert True"])
    focus = review_packet(root)["review_focus"]
    assert not any("long_function" in item for item in focus)


def test_simplicity_focus_reports_large_growth_caused_by_diff(tmp_path: Path) -> None:
    before = "def growing():\n" + "".join("    pass\n" for _ in range(70))
    after = "def growing():\n" + "".join("    pass\n" for _ in range(120))
    root = make_repo(tmp_path, before)
    prepare(root, "grow function", ["app.py"])
    (root / "app.py").write_text(after, encoding="utf-8")
    record_validation(root, [sys.executable, "-c", "assert True"])
    focus = review_packet(root)["review_focus"]
    assert any("growing" in item and "grew by 50 lines" in item for item in focus)
