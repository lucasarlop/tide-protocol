from __future__ import annotations

import subprocess
from pathlib import Path

from tide import mcp


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


def test_lock_list_returns_record_shaped_structured_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = make_repo(tmp_path)
    monkeypatch.setattr(mcp, "project_root", lambda: root)

    result = mcp.call_tool("lock_list", {})

    assert result == {"locks": [], "count": 0}
    assert mcp._tool_summary("lock_list", result) == "lock_list: 0 lock(s)"
