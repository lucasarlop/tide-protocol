from __future__ import annotations

import sys
from pathlib import Path

from tide.core import check, convergence, prepare, record_validation


def fail(repo: Path, label: str) -> None:
    record_validation(repo, [sys.executable, "-c", f"print('FAILED {label}'); raise AssertionError('{label}')"])


def test_two_failed_corrections_switch_to_investigation(repo: Path) -> None:
    prepare(repo, "hard fix", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    fail(repo, "one")
    fail(repo, "two")
    report = check(repo)
    assert report["convergence"]["status"] == "investigating"
    assert report["next_action"].startswith("stop editing")
    assert report["agent_should_continue"] is True


def test_new_evidence_without_root_cause_asks_user(repo: Path) -> None:
    prepare(repo, "hard fix", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    fail(repo, "one")
    fail(repo, "two")
    report = convergence(
        repo,
        summary="Failure begins before packaging and only affects idless assets",
        new_evidence=True,
        root_cause_known=False,
        next_step="instrument asset identity normalization",
    )
    assert report["user_action_required"] is True
    assert report["decision_request"]["options"] == ["continue_one_cycle", "stop_and_report"]
    assert report["agent_should_continue"] is False


def test_continue_grants_one_bounded_cycle(repo: Path) -> None:
    prepare(repo, "hard fix", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    fail(repo, "one")
    fail(repo, "two")
    convergence(repo, summary="new evidence", new_evidence=True, root_cause_known=False, next_step="inspect normalizer")
    report = convergence(repo, decision="continue_one_cycle")
    assert report["user_action_required"] is False
    assert report["convergence"]["cycle_grants"] == 1
    assert report["convergence"]["status"] == "investigating"


def test_stop_decision_allows_agent_to_end_with_report(repo: Path) -> None:
    prepare(repo, "hard fix", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    fail(repo, "one")
    fail(repo, "two")
    convergence(repo, summary="new evidence", new_evidence=True, root_cause_known=False, next_step="inspect normalizer")
    report = convergence(repo, decision="stop_and_report")
    assert report["ready"] is False
    assert report["agent_should_continue"] is False
    assert report["next_action"].startswith("report the current diagnosis")


def test_known_root_cause_returns_to_correction(repo: Path) -> None:
    prepare(repo, "hard fix", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    fail(repo, "one")
    fail(repo, "two")
    report = convergence(repo, summary="decoder changes asset identity", new_evidence=True, root_cause_known=True, next_step="preserve original identity")
    assert report["convergence"]["status"] == "progressing"
    assert report["user_action_required"] is False


def test_authorized_cycle_returns_to_checkpoint_after_one_failed_cycle(repo: Path) -> None:
    prepare(repo, "hard fix", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    fail(repo, "one")
    fail(repo, "two")
    convergence(repo, summary="first evidence", new_evidence=True, root_cause_known=False, next_step="inspect normalizer")
    convergence(repo, decision="continue_one_cycle")
    fail(repo, "cycle")
    report = convergence(repo, summary="more evidence", new_evidence=True, root_cause_known=False, next_step="inspect identity source")
    assert report["user_action_required"] is True
    assert report["decision_request"]["kind"] == "investigation_continuation"
