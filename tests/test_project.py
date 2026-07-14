from __future__ import annotations

import subprocess
from pathlib import Path

from tide.project import changed_files, current_diff, diff_fingerprint


def test_rename_includes_old_and_new_paths(repo: Path) -> None:
    subprocess.run(["git", "mv", "app.py", "renamed.py"], cwd=repo, check=True)
    assert changed_files(repo) == ["app.py", "renamed.py"]
    diff = current_diff(repo)
    assert "renamed.py" in diff["text"]
    assert diff_fingerprint(repo)
