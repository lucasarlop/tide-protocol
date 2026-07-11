from __future__ import annotations

import subprocess
from pathlib import Path

from tide.project import changed_files, current_diff


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


def test_rename_contains_old_and_new_paths_and_complete_diff(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Tide Test")
    (root / "old.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", "old.py")
    git(root, "commit", "-m", "init")
    git(root, "mv", "old.py", "new.py")

    files = changed_files(root)
    assert files == ["new.py", "old.py"]
    diff = current_diff(root, files)["text"]
    assert "rename from old.py" in diff
    assert "rename to new.py" in diff
