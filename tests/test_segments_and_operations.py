from __future__ import annotations

import sys
from pathlib import Path

from tide.core import (
    check,
    create_review_packet,
    get_review_packet,
    operational_verify,
    prepare,
    record_validation,
    reopen,
    split,
    submit_review,
)
from tide.project import load_runtime


def test_split_preserves_compatible_validation(repo: Path) -> None:
    prepare(repo, "change files", ["app.py", "helper.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "helper.py").write_text("HELPER = 2\n", encoding="utf-8")
    record_validation(repo, [sys.executable, "-c", "assert True"], covers=["app.py", "helper.py"], phase="final")
    report = split(repo, task="finish app", files=["app.py"])
    assert report["inherited_validation_count"] == 1
    assert load_runtime(repo)["validations"][0]["files"] == ["app.py"]


def test_reopen_approved_code_for_edit_needs_no_user_authorization(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(repo, [sys.executable, "-c", "assert True"], phase="final")
    summary = create_review_packet(repo)
    packet = get_review_packet(repo, summary["review_id"])
    submit_review(repo, review_id=summary["review_id"], submission_token=packet["submission_token"], approved=True, findings=[])
    report = reopen(repo, reason="verified clipping defect", code_change_required=True)
    assert report["lifecycle"] == "active"
    assert report["user_action_required"] is False
    assert report["approval_proof"] is None


def test_operational_verification_does_not_reopen_code(repo: Path) -> None:
    prepare(repo, "change app", ["app.py"])
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    record_validation(repo, [sys.executable, "-c", "assert True"], phase="final")
    summary = create_review_packet(repo)
    packet = get_review_packet(repo, summary["review_id"])
    submit_review(repo, review_id=summary["review_id"], submission_token=packet["submission_token"], approved=True, findings=[])
    report = reopen(repo, reason="verify runtime")
    assert report["lifecycle"] == "approved"
    operational_verify(repo, name="health", passed=True, details="ok")
    assert check(repo)["ready"] is True
