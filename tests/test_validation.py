from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tide.core import (
    check,
    prepare,
    record_validation,
    revise,
    start_validation,
    validation_log,
    validation_wait,
)
from tide.project import TideError


def test_validation_covers_changed_files_and_becomes_stale(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(repo, [sys.executable, "-c", "assert True"], covers=["app.py"])
    assert check(repo)["uncovered_validation_files"] == []
    (repo / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    report = check(repo)
    assert report["uncovered_validation_files"] == ["app.py"]
    assert report["stale_validation_count"] == 1


def test_final_validation_reuses_same_fingerprint(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    command = [sys.executable, "-c", "assert True"]
    first = record_validation(repo, command, phase="final")
    second = record_validation(repo, command, phase="final")
    assert second["reused"] is True
    assert second["log_id"] == first["log_id"]


def test_shell_wrapper_satisfies_required_validation(repo: Path) -> None:
    required = "python -c 'assert True'"
    prepare(repo, "change app", ["app.py"], [required])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(repo, ["sh", "-lc", required], phase="final")
    assert check(repo)["missing_required_validations"] == []


def test_broad_command_does_not_guess_narrow_equivalence(repo: Path) -> None:
    required = "./scripts/run_tests.sh tests/unit/test_app.py"
    prepare(repo, "change app", ["app.py"], [required])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(repo, ["./scripts/run_tests.sh", "tests/unit/"], phase="final")
    assert check(repo)["missing_required_validations"] == [required]


def test_revise_preserves_only_current_passing_evidence(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(repo, [sys.executable, "-c", "assert True"], phase="final")
    report = revise(repo, add_required_validations=[f"{sys.executable} -c 'assert True'"])
    assert report["current_validation_count"] == 1


def test_failed_validation_returns_saved_log(repo: Path) -> None:
    prepare(repo, "break app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    result = record_validation(repo, [sys.executable, "-c", "print('FAILED demo'); raise AssertionError('boom')"])
    assert result["passed"] is False
    assert result["failure_summary"]
    assert result["agent_should_continue"] is True
    payload = validation_log(repo, result["log_id"])
    assert "AssertionError" in payload["content"]


def test_second_synchronous_failure_switches_to_investigation(repo: Path) -> None:
    prepare(repo, "hard fix", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    command = [sys.executable, "-c", "print('FAILED demo'); raise AssertionError('boom')"]
    first = record_validation(repo, command)
    second = record_validation(repo, command)

    assert first["next_action"].startswith("inspect the saved failure summary")
    assert second["convergence"]["status"] == "investigating"
    assert second["next_action"].startswith("stop editing")
    assert second["agent_should_continue"] is True


def test_background_validation_wait_returns_log_and_summary(repo: Path) -> None:
    prepare(repo, "break app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    started = start_validation(repo, [sys.executable, "-c", "print('FAILED demo'); raise AssertionError('boom')"])
    result = validation_wait(repo, started["validation_id"], wait_seconds=20)
    assert result["status"] == "completed"
    assert result["passed"] is False
    assert result["log_id"].startswith("validation-")
    assert result["failure_summary"]
    assert validation_log(repo, started["validation_id"])["log_id"] == result["log_id"]


def test_validation_requires_changed_task_files(repo: Path) -> None:
    prepare(repo, "no change", ["app.py"])
    with pytest.raises(TideError, match="requires changed files"):
        record_validation(repo, [sys.executable, "-c", "assert True"])
