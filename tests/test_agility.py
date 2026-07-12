from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tide.core import (
    authorize,
    check,
    create_review_packet,
    get_review_packet,
    prepare,
    record_validation,
    reopen,
    revise,
    submit_review,
)
from tide.project import TideError


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )


def make_repo(tmp_path: Path, files: dict[str, str] | None = None) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Tide Test")
    for name, text in (files or {"app.py": "VALUE = 1\n"}).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "init")
    return root


def test_scoped_validation_survives_unrelated_delta_and_reports_only_gap(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"app.py": "VALUE = 1\n", "ui.ts": "export const value = 1;\n"})
    report = prepare(root, "small feature", ["app.py", "ui.ts"])
    assert report["mode"] == "fast"

    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"], covers=["app.py"])
    (root / "ui.ts").write_text("export const value = 2;\n", encoding="utf-8")

    blocked = check(root)
    assert blocked["current_validation_count"] == 1
    assert blocked["stale_validation_count"] == 0
    assert blocked["uncovered_validation_files"] == ["ui.ts"]
    assert "changed files lack current validation coverage" in blocked["blockers"]

    record_validation(root, ["python", "-c", "assert True"], covers=["ui.ts"], phase="final")
    ready = check(root)
    assert ready["ready"]
    assert ready["current_validation_count"] == 2


def test_review_after_first_cycle_contains_only_new_delta(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"app.py": "VALUE = 1\n", "a.py": "A = 1\n", "b.py": "B = 1\n", "c.py": "C = 1\n"})
    prepare(root, "change several files", ["app.py", "a.py", "b.py", "c.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "a.py").write_text("A = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"], covers=["app.py"])
    record_validation(root, ["python", "-c", "assert True"], covers=["a.py"])

    first = create_review_packet(root)
    assert first["review_mode"] == "full"
    packet = get_review_packet(root, first["review_id"])
    submit_review(root, review_id=first["review_id"], submission_token=packet["submission_token"], approved=False, findings=[{"severity": "blocking", "message": "app behavior is incomplete"}])

    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"], covers=["app.py"])
    second = create_review_packet(root)
    detail = get_review_packet(root, second["review_id"])

    assert second["review_mode"] == "incremental"
    assert detail["files"] == ["app.py"]
    assert detail["review_base_id"] == first["review_id"]
    assert detail["previous_findings"][0]["severity"] == "blocking"


def test_follow_up_does_not_block_and_approved_review_locks_scope(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"app.py": "VALUE = 1\n", "a.py": "A = 1\n", "b.py": "B = 1\n", "c.py": "C = 1\n"})
    prepare(root, "change several files", ["app.py", "a.py", "b.py", "c.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"], phase="final")
    meta = create_review_packet(root)
    packet = get_review_packet(root, meta["review_id"])

    review = submit_review(root, review_id=meta["review_id"], submission_token=packet["submission_token"], approved=True, findings=[{"severity": "follow_up", "message": "extract helper later"}])

    assert review["approved"]
    report = check(root)
    assert report["ready"]
    assert report["closure_locked"]
    assert report["follow_up_tasks"] == ["extract helper later"]

    with pytest.raises(TideError, match="closure is locked"):
        revise(root, task="extra cleanup")

    reopened = reopen(root, reason="verify approved runtime")
    assert reopened["lifecycle"] == "operational_verification"
    assert reopened["closure_locked"]
    assert reopened["mutation_allowed"] is False


def test_repeated_scope_expansion_requires_split_or_explicit_extension(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"app.py": "VALUE = 1\n", "a.py": "A = 1\n", "b.py": "B = 1\n", "c.py": "C = 1\n"})
    prepare(root, "small refactor", ["app.py"])
    revise(root, add_files=["a.py"])
    revise(root, add_files=["b.py"])
    report = revise(root, add_files=["c.py"])

    assert report["split_required"]
    assert "scope expansion budget exceeded" in report["split_reasons"]
    assert "extended_investigation" in report["pending_hardgates"]
    assert not report["mutation_allowed"]

    extended = authorize(root, gates=["extended_investigation"])
    assert extended["mutation_allowed"]
    assert extended["split_required"]


def test_sensitive_change_uses_strict_mode_without_file_count_heuristic(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    fast = prepare(root, "rename local helper", ["app.py"])
    assert fast["mode"] == "fast"

    strict = prepare(root, "apply database migration", ["app.py"])
    assert strict["mode"] == "strict"
    assert "database" in strict["pending_hardgates"]
