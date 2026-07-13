from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tide.core import (
    check,
    create_review_packet,
    prepare,
    preparation_report,
    record_validation,
    revise,
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


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Tide Test")
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "init")
    return root


def test_shell_wrapper_satisfies_equivalent_mandatory_validation(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    required = "cd . && python -c 'assert True'"
    prepare(root, "change app", ["app.py"], [required])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    record_validation(
        root,
        ["sh", "-lc", required],
        covers=["app.py"],
        phase="final",
    )

    report = check(root)
    assert report["missing_required_validations"] == []
    assert report["required_validation_status"] == [
        {
            "required": required,
            "matched": True,
            "matched_command": f"sh -lc {required}",
        }
    ]
    assert "required validations are missing for their covered files" not in report["blockers"]


def test_revise_preserves_current_passing_evidence_when_plan_changes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    command = ["python", "-c", "assert True"]
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, command, covers=["app.py"], phase="final")

    report = revise(
        root,
        add_required_validations=["python -c 'assert True'"],
    )

    assert report["current_validation_count"] == 1
    assert report["stale_validation_count"] == 0
    assert report["missing_required_validations"] == []


def test_status_and_review_error_name_exact_missing_validation(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    required = "python -c 'assert True'"
    prepare(root, "change app", ["app.py"], [required])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(
        root,
        ["python", "-c", "assert 1 == 1"],
        covers=["app.py"],
    )

    report = preparation_report(root)
    assert report["missing_required_validations"] == [required]
    assert report["uncovered_validation_files"] == []
    assert report["next_action"] == f"run mandatory validation: {required}"
    assert report["resume"]["next_action"] == f"run mandatory validation: {required}"

    with pytest.raises(TideError, match="review requires mandatory validation") as exc:
        create_review_packet(root)
    assert required in str(exc.value)


def test_revise_discards_stale_or_failed_evidence(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "raise SystemExit(1)"], covers=["app.py"])

    report = revise(root, task="same bounded change")

    assert report["current_validation_count"] == 0
    assert report["uncovered_validation_files"] == ["app.py"]
