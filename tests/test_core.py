from __future__ import annotations

import subprocess
from pathlib import Path

from tide.core import authorize, check, prepare, record_review, record_validation, review_packet


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
    report = prepare(root, "change value", ["app.py"])
    assert report["mutation_allowed"]
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    report = check(root)
    assert not report["ready"]
    assert "no current validation evidence covers the changed task files" in report["blockers"]
    assert report["uncovered_validation_files"] == ["app.py"]

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
    prepare(root, "change app value", ["app.py"])
    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    report = check(root)
    assert not report["ready"]
    assert "independent review required" in report["blockers"]
    record_review(root, approved=True, findings=[])
    assert check(root)["ready"]


def test_hardgate_requires_explicit_authorization(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    report = prepare(root, "deploy database migration to production", ["app.py"])
    assert not report["mutation_allowed"]
    assert set(report["pending_hardgates"]) >= {"database", "production"}

    report = authorize(root, all_gates=True)
    assert report["mutation_allowed"]
    assert not report["pending_hardgates"]

    (root / "app.py").write_text("VALUE = 4\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    record_review(root, approved=True, findings=[])
    assert check(root)["ready"]


def test_review_packet_includes_untracked_diff(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "add helper", ["helper.py"])
    (root / "helper.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    packet = review_packet(root)
    assert packet["files"] == ["helper.py"]
    assert "helper.py" in packet["diff"]["text"]
    assert "def helper" in packet["diff"]["text"]


def test_changed_files_without_boundary_blocks(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    report = prepare(root, "change something")
    assert not report["mutation_allowed"]
    (root / "app.py").write_text("VALUE = 5\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    assert "no boundary declared" in check(root)["blockers"]


def test_validation_becomes_stale_after_code_changes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change value", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    report = check(root)
    assert not report["ready"]
    assert report["stale_validation_count"] == 1
    assert "no current validation evidence covers the changed task files" in report["blockers"]


def test_review_becomes_stale_after_code_changes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    lock = root / ".tide" / "locks" / "app.md"
    lock.parent.mkdir(parents=True)
    lock.write_text(
        """+++
name = \"app\"
paths = [\"app.py\"]
criticality = \"production\"
review_required = true
validations = []
invariants = []
sensitive_changes = []
+++
# App
""",
        encoding="utf-8",
    )
    git(root, "add", ".tide/locks/app.md")
    git(root, "commit", "-m", "add lock")
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    record_review(root, approved=True, findings=[])
    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    report = check(root)
    assert not report["ready"]
    assert "independent review is stale for the current diff" in report["blockers"]


def test_unchanged_preexisting_file_outside_boundary_is_ignored(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "notes.txt").write_text("personal notes\n", encoding="utf-8")
    report = prepare(root, "change app", ["app.py"])
    assert report["mutation_allowed"]
    assert report["preexisting_changes"] == ["notes.txt"]
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    report = check(root)
    assert report["ready"]
    assert report["outside_boundary"] == []
    assert report["all_worktree_changes"] == ["app.py", "notes.txt"]


def test_dirty_file_inside_boundary_requires_authorization(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    report = prepare(root, "continue app change", ["app.py"])
    assert not report["mutation_allowed"]
    assert "dirty_boundary" in report["pending_hardgates"]


def test_sensitive_file_path_creates_hardgate(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    report = prepare(root, "adjust versions", ["pyproject.toml"])
    assert "dependency" in report["pending_hardgates"]
    assert not report["mutation_allowed"]


def test_preexisting_outside_file_changed_after_prepare_blocks(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "notes.txt").write_text("version 1\n", encoding="utf-8")
    prepare(root, "change app", ["app.py"])
    (root / "notes.txt").write_text("version 2\n", encoding="utf-8")
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    report = check(root)
    assert not report["ready"]
    assert report["outside_boundary"] == ["notes.txt"]


def test_actual_sensitive_file_adds_new_pending_hardgate(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "add helper", ["src/**"])
    auth = root / "src" / "auth"
    auth.mkdir(parents=True)
    (auth / "service.py").write_text("TOKEN = None\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    report = check(root)
    assert not report["ready"]
    assert "auth" in report["pending_hardgates"]
    assert "hardgates not authorized" in report["blockers"]


def test_fingerprint_uses_full_diff_beyond_review_truncation(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    large = root / "large.txt"
    large.write_text("a" * 130_000 + "1\n", encoding="utf-8")
    git(root, "add", "large.txt")
    git(root, "commit", "-m", "large")
    prepare(root, "change large file", ["large.txt"])
    large.write_text("a" * 130_000 + "2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    large.write_text("a" * 130_000 + "3\n", encoding="utf-8")
    report = check(root)
    assert not report["ready"]
    assert report["stale_validation_count"] == 1
