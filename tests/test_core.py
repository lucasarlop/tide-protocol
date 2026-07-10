from __future__ import annotations

import subprocess
from pathlib import Path

from tide.core import check, prepare, record_review, record_validation


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


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


def test_boundary_and_validation_gate(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change value", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    report = check(root)
    assert not report["ready"]
    assert "no validation recorded" in report["blockers"]

    result = record_validation(root, ["python", "-c", "assert True"])
    assert result["passed"]
    assert check(root)["ready"]


def test_file_outside_boundary_blocks(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change value", ["app.py"])
    (root / "other.py").write_text("x = 1\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    report = check(root)
    assert not report["ready"]
    assert report["outside_boundary"] == ["other.py"]


def test_module_lock_requires_review_and_command(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    lock = root / ".tide" / "locks" / "app.md"
    lock.parent.mkdir(parents=True)
    lock.write_text(
        '''+++
name = "app"
paths = ["app.py"]
criticality = "production"
review_required = true
validations = ["python -c assert True"]
invariants = []
sensitive_changes = []
+++
# App
''',
        encoding="utf-8",
    )
    git(root, "add", ".tide/locks/app.md")
    git(root, "commit", "-m", "add lock")
    prepare(root, "change production app", ["app.py"])
    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    report = check(root)
    assert not report["ready"]
    assert "independent review required" in report["blockers"]
    record_review(root, approved=True, findings=[])
    assert check(root)["ready"]
