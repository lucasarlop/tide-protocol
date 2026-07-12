from __future__ import annotations

from pathlib import Path

from tide import setup_tools


def test_setup_installs_balanced_and_critical_reviewers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(setup_tools.shutil, "which", lambda name: None)

    actions = setup_tools.setup_global(codex=True, opencode=True)

    codex_agents = tmp_path / ".codex" / "agents"
    opencode_agents = tmp_path / ".config" / "opencode" / "agents"

    assert (codex_agents / "tide-reviewer.toml").exists()
    assert (codex_agents / "tide-reviewer-critical.toml").exists()
    assert 'model = "gpt-5.6-terra"' in (
        codex_agents / "tide-reviewer.toml"
    ).read_text(encoding="utf-8")
    assert 'model = "gpt-5.6-sol"' in (
        codex_agents / "tide-reviewer-critical.toml"
    ).read_text(encoding="utf-8")

    assert (opencode_agents / "tide-reviewer.md").exists()
    assert (opencode_agents / "tide-reviewer-critical.md").exists()
    assert "model: openai/gpt-5.6-terra" in (
        opencode_agents / "tide-reviewer.md"
    ).read_text(encoding="utf-8")
    assert "model: openai/gpt-5.6-sol" in (
        opencode_agents / "tide-reviewer-critical.md"
    ).read_text(encoding="utf-8")

    assert any("install critical reviewer" in item for item in actions)
