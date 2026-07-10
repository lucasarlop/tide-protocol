from __future__ import annotations

import json
from pathlib import Path

from tide import cli, lifecycle, uninstall
from tide.output import render


def test_human_output_is_not_json() -> None:
    lines = render(
        {
            "status": "ready",
            "boundary": ["src/**"],
            "mutation_allowed": True,
        },
        title="Estado atual",
    )
    text = "\n".join(lines)
    assert text.startswith("Estado atual")
    assert not text.lstrip().startswith("{")
    assert "Status: pronto" in text
    assert "Fronteira:" in text
    assert "Edição permitida: sim" in text


def _patch_status(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "project_root", lambda: tmp_path)
    monkeypatch.setattr(
        cli,
        "preparation_report",
        lambda root: {
            "status": "prepared",
            "boundary": ["src/**"],
            "mutation_allowed": True,
        },
    )


def test_json_flag_can_appear_after_command(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_status(monkeypatch, tmp_path)
    assert cli.main(["status", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "prepared"


def test_default_status_is_human(capsys, monkeypatch, tmp_path: Path) -> None:
    _patch_status(monkeypatch, tmp_path)
    assert cli.main(["status"]) == 0
    output = capsys.readouterr().out
    assert "Estado atual" in output
    assert "Status: preparado" in output
    assert not output.lstrip().startswith("{")


def test_update_dry_run_uses_uv_upgrade(monkeypatch) -> None:
    monkeypatch.setattr(
        lifecycle.shutil,
        "which",
        lambda name: "/usr/bin/uv" if name == "uv" else None,
    )
    monkeypatch.setattr(
        lifecycle,
        "detect_adapters",
        lambda: {"codex": True, "opencode": False},
    )
    result = lifecycle.update_tool(dry_run=True)
    assert result["command"] == [
        "/usr/bin/uv",
        "tool",
        "upgrade",
        "--reinstall",
        "tide-protocol",
    ]
    assert result["adapters"] == ["codex"]


def test_detect_adapters(tmp_path: Path) -> None:
    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "AGENTS.md").write_text("<!-- tide:start -->", encoding="utf-8")
    result = lifecycle.detect_adapters(tmp_path)
    assert result == {"codex": True, "opencode": False}


def test_update_refreshes_installed_adapter(monkeypatch) -> None:
    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stderr = ""
        stdout = '{"actions":["refreshed"]}'

    def which(name: str) -> str | None:
        return {
            "uv": "/usr/bin/uv",
            "tide": "/home/user/.local/bin/tide",
        }.get(name)

    def run(command: list[str], **kwargs) -> Result:
        calls.append(command)
        return Result()

    monkeypatch.setattr(lifecycle.shutil, "which", which)
    monkeypatch.setattr(lifecycle.subprocess, "run", run)
    monkeypatch.setattr(
        lifecycle,
        "detect_adapters",
        lambda: {"codex": True, "opencode": False},
    )

    result = lifecycle.update_tool()

    assert calls[0] == [
        "/usr/bin/uv",
        "tool",
        "upgrade",
        "--reinstall",
        "tide-protocol",
    ]
    assert calls[1] == [
        "/home/user/.local/bin/tide",
        "setup",
        "--json",
        "--codex",
    ]
    assert result["actions"] == ["refreshed"]


def test_uninstall_preserves_unrelated_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "AGENTS.md").write_text(
        "before\n<!-- tide:start -->\ntide\n<!-- tide:end -->\nafter\n",
        encoding="utf-8",
    )
    (codex / "config.toml").write_text(
        '[model]\nname="x"\n\n'
        "# tide:start\n"
        "[mcp_servers.tide]\n"
        'command="tide"\n'
        "# tide:end\n",
        encoding="utf-8",
    )
    (codex / "agents").mkdir()
    (codex / "agents" / "tide-reviewer.toml").write_text("x", encoding="utf-8")

    opencode = tmp_path / ".config" / "opencode"
    (opencode / "agents").mkdir(parents=True)
    (opencode / "AGENTS.md").write_text(
        "base\n<!-- tide:start -->\ntide\n<!-- tide:end -->\n",
        encoding="utf-8",
    )
    (opencode / "agents" / "tide-reviewer.md").write_text("x", encoding="utf-8")
    (opencode / "opencode.json").write_text(
        json.dumps(
            {
                "model": "keep",
                "instructions": [str(opencode / "AGENTS.md"), "other.md"],
                "mcp": {
                    "tide": {"command": ["tide"]},
                    "other": {"command": ["other"]},
                },
                "permission": {
                    "tide_authorize": "ask",
                    "bash": "ask",
                },
            }
        ),
        encoding="utf-8",
    )

    skill = tmp_path / ".agents" / "skills" / "tide"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("x", encoding="utf-8")

    uninstall.uninstall_global(codex=True, opencode=True)

    assert "tide:start" not in (codex / "AGENTS.md").read_text(encoding="utf-8")
    assert "[model]" in (codex / "config.toml").read_text(encoding="utf-8")
    assert not (codex / "agents" / "tide-reviewer.toml").exists()

    data = json.loads((opencode / "opencode.json").read_text(encoding="utf-8"))
    assert data["model"] == "keep"
    assert data["instructions"] == ["other.md"]
    assert "tide" not in data["mcp"]
    assert "other" in data["mcp"]
    assert data["permission"] == {"bash": "ask"}
    assert not skill.exists()


def test_codex_uninstall_keeps_graph_mcp(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "config.toml").write_text(
        "# tide:start\n"
        "[mcp_servers.tide]\n"
        'command = "tide"\n\n'
        "[mcp_servers.code-review-graph]\n"
        'command = "code-review-graph"\n'
        'args = ["serve"]\n'
        "# tide:end\n",
        encoding="utf-8",
    )

    uninstall.uninstall_global(codex=True, opencode=False)

    text = (codex / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.tide]" not in text
    assert "[mcp_servers.code-review-graph]" in text


def test_partial_uninstall_keeps_shared_skill(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    skill = tmp_path / ".agents" / "skills" / "tide"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("x", encoding="utf-8")

    uninstall.uninstall_global(
        codex=True,
        opencode=False,
        remove_shared=False,
    )

    assert skill.exists()
