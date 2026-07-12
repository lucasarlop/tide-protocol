from __future__ import annotations

from pathlib import Path

from tide import setup_tools, uninstall


def test_setup_installs_and_uninstall_removes_both_reviewers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(setup_tools.shutil, "which", lambda name: None)

    actions = setup_tools.setup_global(codex=True, opencode=True)

    codex_agents = tmp_path / ".codex" / "agents"
    opencode_agents = tmp_path / ".config" / "opencode" / "agents"
    reviewer_paths = [
        codex_agents / "tide-reviewer.toml",
        codex_agents / "tide-reviewer-critical.toml",
        opencode_agents / "tide-reviewer.md",
        opencode_agents / "tide-reviewer-critical.md",
    ]

    assert all(path.exists() for path in reviewer_paths)
    assert 'model = "gpt-5.6-terra"' in reviewer_paths[0].read_text(
        encoding="utf-8"
    )
    assert 'model = "gpt-5.6-sol"' in reviewer_paths[1].read_text(
        encoding="utf-8"
    )
    assert "model: openai/gpt-5.6-terra" in reviewer_paths[2].read_text(
        encoding="utf-8"
    )
    assert "model: openai/gpt-5.6-sol" in reviewer_paths[3].read_text(
        encoding="utf-8"
    )
    assert any("install critical reviewer" in item for item in actions)

    uninstall.uninstall_global(codex=True, opencode=True)

    assert all(not path.exists() for path in reviewer_paths)
