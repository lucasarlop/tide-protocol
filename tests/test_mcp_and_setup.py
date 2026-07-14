from __future__ import annotations

import json
from pathlib import Path

from tide import mcp
from tide.cli import main
from tide.protocol import WRITER_INSTRUCTIONS
from tide.setup_tools import _merge_opencode, _patch_codex_config, setup_global


def test_mcp_surface_is_small_and_complete() -> None:
    assert {tool["name"] for tool in mcp.tools()} == {
        "resume", "prepare", "revise", "split", "reopen", "validate",
        "validation_wait", "validation_log", "convergence", "review_packet",
        "review_get", "review_submit", "operational_verify", "authorize",
        "check", "commit_check",
    }


def test_mcp_initialize_exposes_single_protocol(capsys) -> None:
    mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    result = json.loads(capsys.readouterr().out)["result"]
    assert result["serverInfo"]["version"] == "1.2.0"
    assert result["instructions"] == WRITER_INSTRUCTIONS
    assert "call resume automatically" in result["instructions"]
    assert "continue one bounded cycle" in result["instructions"]


def test_review_schema_requires_complete_findings() -> None:
    schema = next(tool for tool in mcp.tools() if tool["name"] == "review_submit")["inputSchema"]
    required = schema["properties"]["findings"]["items"]["required"]
    assert required == ["id", "severity", "message", "paths", "expected_action"]


def test_mcp_text_summaries_are_compact() -> None:
    text = mcp._tool_summary("check", {"lifecycle": "active", "ready": False, "primary_blocker": "review required", "next_action": "review"})
    assert "review required" in text
    assert len(text) < 180


def test_setup_does_not_manage_code_review_graph(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    setup_global(codex=True, opencode=True)
    codex = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    opencode = json.loads((tmp_path / ".config" / "opencode" / "opencode.json").read_text(encoding="utf-8"))
    assert "code-review-graph" not in codex
    assert "code-review-graph" not in opencode["mcp"]
    assert opencode["permission"]["tide_authorize"] == "ask"


def test_setup_preserves_unrelated_jsonc(tmp_path: Path) -> None:
    path = tmp_path / "opencode.json"
    path.write_text('{\n // comment\n "theme": "dark",\n}\n', encoding="utf-8")
    _merge_opencode(path, bootstrap_path=tmp_path / "AGENTS.md")
    config = json.loads(path.read_text(encoding="utf-8"))
    assert config["theme"] == "dark"
    assert config["mcp"]["tide"]["command"] == ["tide", "mcp", "serve"]


def test_codex_config_prompts_only_for_authorize(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    _patch_codex_config(path)
    text = path.read_text(encoding="utf-8")
    assert '[mcp_servers.tide.tools.authorize]' in text
    assert 'approval_mode = "prompt"' in text


def test_cli_help_is_simple(capsys) -> None:
    assert main([]) == 0
    output = capsys.readouterr().out
    assert "resume" in output
    assert "status" in output
    assert "check" in output
    assert "validate" not in output
