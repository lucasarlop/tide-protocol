from __future__ import annotations

import json
from pathlib import Path

from tide import entrypoint


def test_hook_install_command_reports_installed_hook(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(entrypoint, "project_root", lambda: tmp_path)
    monkeypatch.setattr(
        entrypoint,
        "ensure_commit_hook",
        lambda root: {"installed": True, "path": str(root / ".git/hooks/pre-commit"), "managed": True},
    )
    monkeypatch.setattr(entrypoint.sys, "argv", ["tide", "hook", "install"])

    entrypoint.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["installed"] is True
    assert payload["managed"] is True
    assert payload["path"].endswith(".git/hooks/pre-commit")
