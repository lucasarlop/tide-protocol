from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tide import mcp
from tide.core import (
    check,
    create_review_packet,
    get_review_packet,
    prepare,
    record_validation,
    submit_review,
)
from tide.project import TideError


def validated_change(repo: Path, *, path: str = "app.py") -> None:
    prepare(repo, "change code", [path])
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(repo, [sys.executable, "-c", "assert True"], phase="final")


def submit(repo: Path, summary: dict, *, approved: bool, findings: list[dict]) -> dict:
    packet = get_review_packet(repo, summary["review_id"])
    return submit_review(repo, review_id=summary["review_id"], submission_token=packet["submission_token"], approved=approved, findings=findings)


def test_code_change_requires_independent_review(repo: Path) -> None:
    validated_change(repo)
    report = check(repo)
    assert "independent review required" in report["blockers"]
    summary = create_review_packet(repo)
    assert summary["reviewer_agent"] == "tide-reviewer"
    submit(repo, summary, approved=True, findings=[])
    assert check(repo)["ready"] is True


def test_sensitive_code_uses_critical_reviewer(repo: Path) -> None:
    path = "src/auth/service.py"
    validated_change(repo, path=path)
    summary = create_review_packet(repo)
    assert summary["reviewer_agent"] == "tide-reviewer-critical"


def test_blocking_finding_requires_correction_and_incremental_review(repo: Path) -> None:
    validated_change(repo)
    first = create_review_packet(repo)
    submit(
        repo,
        first,
        approved=False,
        findings=[{"id": "wrong-value", "severity": "blocking", "message": "Value is wrong", "paths": ["app.py:1"], "expected_action": "Use value 3"}],
    )
    assert "independent review has blocking findings" in check(repo)["blockers"]
    (repo / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    record_validation(repo, [sys.executable, "-c", "assert True"])
    second = create_review_packet(repo)
    assert second["files"] == ["app.py"]
    submit(repo, second, approved=True, findings=[])
    assert check(repo)["ready"] is True


def test_follow_up_does_not_block_approval(repo: Path) -> None:
    validated_change(repo)
    summary = create_review_packet(repo)
    review = submit(
        repo,
        summary,
        approved=True,
        findings=[{"id": "cleanup", "severity": "follow_up", "message": "Optional cleanup", "paths": ["app.py:1"], "expected_action": "Refactor later"}],
    )
    assert review["approved"] is True
    assert check(repo)["ready"] is True


def test_edit_after_approval_invalidates_review(repo: Path) -> None:
    validated_change(repo)
    summary = create_review_packet(repo)
    submit(repo, summary, approved=True, findings=[])
    (repo / "app.py").write_text("VALUE = 4\n", encoding="utf-8")
    report = check(repo)
    assert report["ready"] is False
    assert report["approval_proof"] is None


def test_truncated_packet_cannot_be_approved(repo: Path) -> None:
    large = repo / "large.txt"
    large.write_text("a" * 130_000 + "\n", encoding="utf-8")
    import subprocess
    subprocess.run(["git", "add", "large.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "large"], cwd=repo, check=True, capture_output=True)
    prepare(repo, "change large", ["large.txt"])
    large.write_text("b" * 130_000 + "\n", encoding="utf-8")
    record_validation(repo, [sys.executable, "-c", "assert True"])
    summary = create_review_packet(repo, full=True)
    packet = get_review_packet(repo, summary["review_id"])
    with pytest.raises(TideError, match="truncated"):
        submit_review(repo, review_id=summary["review_id"], submission_token=packet["submission_token"], approved=True, findings=[])


def test_duplicate_submission_is_idempotent_only_at_mcp(repo: Path, monkeypatch) -> None:
    validated_change(repo)
    summary = create_review_packet(repo)
    packet = get_review_packet(repo, summary["review_id"])
    args = {"review_id": summary["review_id"], "submission_token": packet["submission_token"], "approved": True, "findings": []}
    monkeypatch.chdir(repo)
    first = mcp.call_tool("review_submit", args)
    second = mcp.call_tool("review_submit", args)
    assert first["idempotent"] is False
    assert second["idempotent"] is True
    assert second["receipt_id"] == first["receipt_id"]
