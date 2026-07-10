from __future__ import annotations

import json
import shutil
from importlib.resources import files
from pathlib import Path
from typing import Any


START = "<!-- tide:start -->"
END = "<!-- tide:end -->"


def setup_global(*, codex: bool, opencode: bool, dry_run: bool = False) -> list[str]:
    actions: list[str] = []
    home = Path.home()
    asset_root = files("tide").joinpath("assets")

    skill_source = asset_root.joinpath("skill")
    skill_target = home / ".agents" / "skills" / "tide"
    actions.append(f"install skill -> {skill_target}")
    if not dry_run:
        _copy_tree(skill_source, skill_target)

    if codex:
        codex_dir = home / ".codex"
        actions.extend([
            f"patch bootstrap -> {codex_dir / 'AGENTS.md'}",
            f"install reviewer -> {codex_dir / 'agents' / 'tide-reviewer.toml'}",
            f"register MCP -> {codex_dir / 'config.toml'}",
        ])
        if not dry_run:
            _patch_markdown(codex_dir / "AGENTS.md", asset_root.joinpath("adapters/codex/AGENTS.md").read_text())
            _copy_file(asset_root.joinpath("adapters/codex/tide-reviewer.toml"), codex_dir / "agents" / "tide-reviewer.toml")
            _patch_text_block(
                codex_dir / "config.toml",
                "# tide:start",
                "# tide:end",
                '[mcp_servers.tide]\ncommand = "tide"\nargs = ["mcp", "serve"]\n',
            )

    if opencode:
        config_dir = home / ".config" / "opencode"
        actions.extend([
            f"patch bootstrap -> {config_dir / 'AGENTS.md'}",
            f"install reviewer -> {config_dir / 'agents' / 'tide-reviewer.md'}",
            f"register MCP -> {config_dir / 'opencode.json'}",
        ])
        if not dry_run:
            _patch_markdown(config_dir / "AGENTS.md", asset_root.joinpath("adapters/opencode/AGENTS.md").read_text())
            _copy_file(asset_root.joinpath("adapters/opencode/tide-reviewer.md"), config_dir / "agents" / "tide-reviewer.md")
            _merge_opencode(config_dir / "opencode.json")

    return actions


def _copy_tree(source: Any, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        destination = target / child.name
        if child.is_dir():
            _copy_tree(child, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(child.read_text(), encoding="utf-8")


def _copy_file(source: Any, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(), encoding="utf-8")


def _patch_markdown(path: Path, content: str) -> None:
    _patch_text_block(path, START, END, content.strip() + "\n")


def _patch_text_block(path: Path, start: str, end: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    block = f"{start}\n{content.rstrip()}\n{end}\n"
    if start in current and end in current:
        prefix, tail = current.split(start, 1)
        _, suffix = tail.split(end, 1)
        updated = prefix.rstrip() + "\n\n" + block + suffix.lstrip("\n")
    else:
        updated = current.rstrip() + ("\n\n" if current.strip() else "") + block
    path.write_text(updated, encoding="utf-8")


def _merge_opencode(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = path.with_suffix(".json.tide-backup")
            shutil.copy2(path, backup)
            config = {}
    else:
        config = {}
    config.setdefault("$schema", "https://opencode.ai/config.json")
    config.setdefault("mcp", {})["tide"] = {
        "type": "local",
        "command": ["tide", "mcp", "serve"],
    }
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
