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
    record_review,
    record_validation,
    revise,
    validation_log,
)
from tide.mcp import tools
from tide.policy import decide
from tide.project import TideError


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


def test_revise_preserves_baseline_and_requires_scope_expansion_authorization(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "helper.py").write_text("HELPER = 1\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])

    report = revise(root, add_files=["helper.py"])

    assert report["revision"] == 1
    assert report["boundary"] == ["app.py", "helper.py"]
    assert "dirty_boundary" not in report["pending_hardgates"]
    assert "scope_expansion" in report["pending_hardgates"]
    assert not report["mutation_allowed"]

    report = authorize(root, gates=["scope_expansion"])
    assert report["mutation_allowed"]
    checked = check(root)
    assert checked["current_validation_count"] == 1
    assert checked["uncovered_validation_files"] == ["helper.py"]


def test_revise_adding_original_dirty_file_requires_authorization(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "notes.txt").write_text("personal\n", encoding="utf-8")
    prepare(root, "change app", ["app.py"])

    report = revise(root, add_files=["notes.txt"])

    assert "dirty_boundary" in report["pending_hardgates"]
    assert "scope_expansion" in report["pending_hardgates"]
    assert not report["mutation_allowed"]


def test_validation_returns_compact_evidence_and_persists_full_log(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    evidence = record_validation(
        root,
        ["python", "-c", "print('line1'); print('line2')"],
    )

    assert evidence["passed"]
    assert "stdout" not in evidence
    assert "stderr" not in evidence
    assert evidence["stdout_tail"] == ["line1", "line2"]
    full = validation_log(root, evidence["log_id"])
    assert "line1" in full["content"]
    assert "line2" in full["content"]


def test_review_packet_summary_hides_diff_from_writer(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])

    summary = create_review_packet(root)

    assert "diff" not in summary
    assert summary["review_id"].startswith("review-")
    detail = get_review_packet(root, summary["review_id"])
    assert detail["current"]
    assert "VALUE = 2" in detail["diff"]["text"]


def test_review_id_cannot_be_recorded_after_diff_changes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change app", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])
    review_id = create_review_packet(root)["review_id"]
    (root / "app.py").write_text("VALUE = 3\n", encoding="utf-8")

    with pytest.raises(TideError, match="stale"):
        record_review(root, approved=True, findings=[], review_id=review_id)


def test_setup_py_is_dependency_hardgate() -> None:
    decision = decide("configure package", ["setup.py"], [])
    assert "dependency" in decision.hardgates


def test_large_new_file_triggers_simplicity_review(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "add generated runner", ["runner.py"])
    (root / "runner.py").write_text("\n".join(f"x_{i} = {i}" for i in range(450)) + "\n", encoding="utf-8")
    record_validation(root, ["python", "-c", "assert True"])

    report = check(root)

    assert report["review_required"]
    assert any(reason.startswith("simplicity:") for reason in report["review_reasons"])
    assert "independent review required" in report["blockers"]


def test_mcp_surface_has_revise_and_lazy_artifact_tools() -> None:
    names = {item["name"] for item in tools()}
    assert {"revise", "reopen", "validation_log", "review_packet", "review_get"} <= names
