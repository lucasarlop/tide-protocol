from __future__ import annotations

from pathlib import Path

from tide.core import authorize, check, external_acknowledge, prepare, revise
from tide.policy import decide


def test_empty_boundary_allows_reading_but_not_mutation(repo: Path) -> None:
    report = prepare(repo, "discover implementation")
    assert report["mutation_allowed"] is False
    assert report["next_action"].startswith("inspect the live code")


def test_boundary_expansion_is_autonomous(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "new.py").write_text("NEW = 1\n", encoding="utf-8")
    report = revise(repo, add_files=["new.py"])
    assert report["boundary"] == ["app.py", "new.py"]
    assert "scope_expansion" not in report["pending_hardgates"]
    assert report["mutation_allowed"] is True


def test_changed_file_outside_boundary_blocks(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "other.py").write_text("OTHER = 1\n", encoding="utf-8")
    report = check(repo)
    assert report["outside_boundary"] == ["other.py"]
    assert report["ready"] is False


def test_preexisting_unchanged_outside_file_does_not_block(repo: Path) -> None:
    (repo / "notes.txt").write_text("personal\n", encoding="utf-8")
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    assert check(repo)["outside_boundary"] == []


def test_external_change_can_be_acknowledged(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "session.md").write_text("client export\n", encoding="utf-8")
    assert check(repo)["outside_boundary"] == ["session.md"]
    report = external_acknowledge(repo, ["session.md"], reason="client export")
    assert report["outside_boundary"] == []


def test_technical_risk_requires_critical_review_not_authorization() -> None:
    decision = decide("change authentication database adapter", ["src/auth/service.py"], [])
    assert decision.authorization_gates == ()
    assert {"auth", "database"} <= set(decision.risk_signals)
    assert decision.review_level == "critical"


def test_production_action_requires_authorization(repo: Path) -> None:
    report = prepare(repo, "deploy migration to production", ["app.py"])
    assert report["pending_hardgates"] == ["production"]
    assert report["user_action_required"] is True
    authorized = authorize(repo, gates=["production"])
    assert authorized["pending_hardgates"] == []


def test_destructive_real_data_action_requires_authorization() -> None:
    decision = decide("delete production data rows", ["scripts/cleanup.py"], [])
    assert "destructive_data" in decision.authorization_gates
