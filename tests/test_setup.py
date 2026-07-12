from __future__ import annotations

import json
from pathlib import Path

from tide.setup_tools import _merge_opencode, _patch_codex_config


def test_opencode_jsonc_is_preserved_and_extended(tmp_path: Path) -> None:
    config = tmp_path / "opencode.json"
    bootstrap = tmp_path / "AGENTS.md"
    config.write_text(
        '''{
  // existing user setting
  "model": "openai/gpt-test",
  "instructions": ["existing.md",],
  "permission": {"bash": "ask",},
}
''',
        encoding="utf-8",
    )

    _merge_opencode(config, bootstrap_path=bootstrap, graph_command="/usr/bin/code-review-graph")
    result = json.loads(config.read_text(encoding="utf-8"))
    assert result["model"] == "openai/gpt-test"
    assert result["permission"]["bash"] == "ask"
    assert result["permission"]["tide_authorize"] == "ask"
    assert result["permission"]["tide_validate"] == "allow"
    assert str(bootstrap) in result["instructions"]
    assert result["mcp"]["tide"]["command"] == ["tide", "mcp", "serve"]
    assert result["mcp"]["code-review-graph"]["command"] == ["/usr/bin/code-review-graph", "serve"]
    assert config.with_suffix(".json.tide-backup").exists()


def test_codex_config_prompts_only_for_authorization(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('[model_providers.local]\nname = "local"\n', encoding="utf-8")
    _patch_codex_config(config, graph_command="/usr/bin/code-review-graph")
    text = config.read_text(encoding="utf-8")
    assert "[model_providers.local]" in text
    assert "[mcp_servers.tide.tools.authorize]" in text
    assert 'approval_mode = "prompt"' in text
    assert "[mcp_servers.tide.tools.validate]" not in text
    assert "[mcp_servers.code-review-graph]" in text


def test_codex_does_not_duplicate_existing_graph_server(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        '[mcp_servers.code-review-graph]\ncommand = "custom-crg"\nargs = ["serve"]\n',
        encoding="utf-8",
    )
    _patch_codex_config(config, graph_command="/usr/bin/code-review-graph")
    assert config.read_text(encoding="utf-8").count("[mcp_servers.code-review-graph]") == 1
