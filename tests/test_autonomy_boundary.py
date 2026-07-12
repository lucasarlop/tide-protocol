from __future__ import annotations

import subprocess
from pathlib import Path

from tide.core import authorize, check, prepare, resume


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


def test_pending_hardgate_returns_structured_authorization_request(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    report = prepare(root, "apply database migration", ["app.py"])

    assert report["user_action_required"] is True
    assert report["agent_should_continue"] is False
    assert report["authorization_request"] == {
        "tool": "authorize",
        "arguments": {"gates": ["database"], "all": False},
        "interaction": "client_permission_prompt",
        "message": "Authorize the pending Tide hardgates.",
    }
    assert report["next_action"].startswith("call authorize")

    checkpoint = resume(root)
    assert checkpoint["user_action_required"] is True
    assert checkpoint["authorization_request"]["arguments"]["gates"] == ["database"]

    authorized = authorize(root, gates=["database"])
    assert authorized["user_action_required"] is False
    assert authorized["authorization_request"] is None


def test_validation_and_review_work_do_not_require_user_action(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    prepare(root, "change local helper", ["app.py"])
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    report = check(root)

    assert report["ready"] is False
    assert report["user_action_required"] is False
    assert report["agent_should_continue"] is True
    assert report["authorization_request"] is None
