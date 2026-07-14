from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .project import TideError
from .protocol import CRITICAL_REVIEWER_INSTRUCTIONS, REVIEWER_INSTRUCTIONS, WRITER_INSTRUCTIONS

START = "<!-- tide:start -->"
END = "<!-- tide:end -->"
TOML_START = "# tide:start"
TOML_END = "# tide:end"


def setup_global(*, codex: bool, opencode: bool, dry_run: bool = False) -> list[str]:
    actions: list[str] = []
    home = Path.home()
    skill_target = home / ".agents" / "skills" / "tide" / "SKILL.md"
    actions.append(f"install skill -> {skill_target}")
    if not dry_run:
        skill_target.parent.mkdir(parents=True, exist_ok=True)
        skill_target.write_text(_skill_text(), encoding="utf-8")

    if codex:
        codex_dir = home / ".codex"
        config_path = codex_dir / "config.toml"
        actions.extend(
            [
                f"patch bootstrap -> {codex_dir / 'AGENTS.md'}",
                f"install reviewer -> {codex_dir / 'agents' / 'tide-reviewer.toml'}",
                f"install critical reviewer -> {codex_dir / 'agents' / 'tide-reviewer-critical.toml'}",
                f"register Tide MCP -> {config_path}",
            ]
        )
        if not dry_run:
            _patch_markdown(codex_dir / "AGENTS.md", _bootstrap_text())
            _write(codex_dir / "agents" / "tide-reviewer.toml", _codex_reviewer(False))
            _write(codex_dir / "agents" / "tide-reviewer-critical.toml", _codex_reviewer(True))
            _patch_codex_config(config_path)

    if opencode:
        config_dir = home / ".config" / "opencode"
        config_path = config_dir / "opencode.json"
        bootstrap_path = config_dir / "AGENTS.md"
        actions.extend(
            [
                f"patch bootstrap -> {bootstrap_path}",
                f"install reviewer -> {config_dir / 'agents' / 'tide-reviewer.md'}",
                f"install critical reviewer -> {config_dir / 'agents' / 'tide-reviewer-critical.md'}",
                f"register Tide MCP and instructions -> {config_path}",
            ]
        )
        if not dry_run:
            _patch_markdown(bootstrap_path, _bootstrap_text())
            _write(config_dir / "agents" / "tide-reviewer.md", _opencode_reviewer(False))
            _write(config_dir / "agents" / "tide-reviewer-critical.md", _opencode_reviewer(True))
            _merge_opencode(config_path, bootstrap_path=bootstrap_path)
    return actions


def _skill_text() -> str:
    return (
        "---\n"
        "name: tide\n"
        "description: Quality protocol for autonomous code changes.\n"
        "---\n\n"
        "# Tide 1.2\n\n"
        + WRITER_INSTRUCTIONS
        + "\n"
    )


def _bootstrap_text() -> str:
    return "# Tide\n\n" + WRITER_INSTRUCTIONS + "\n"


def _codex_reviewer(critical: bool) -> str:
    name = "tide-reviewer-critical" if critical else "tide-reviewer"
    description = "Read-only critical Tide reviewer." if critical else "Read-only Tide reviewer."
    model = "gpt-5.6-sol" if critical else "gpt-5.6-terra"
    instructions = CRITICAL_REVIEWER_INSTRUCTIONS if critical else REVIEWER_INSTRUCTIONS
    return (
        f'name = {json.dumps(name)}\n'
        f'description = {json.dumps(description)}\n'
        f'model = {json.dumps(model)}\n'
        'model_reasoning_effort = "high"\n'
        'sandbox_mode = "read-only"\n'
        f'developer_instructions = {json.dumps(instructions)}\n'
    )


def _opencode_reviewer(critical: bool) -> str:
    description = "Read-only critical Tide reviewer." if critical else "Read-only Tide reviewer."
    model = "openai/gpt-5.6-sol" if critical else "openai/gpt-5.6-terra"
    instructions = CRITICAL_REVIEWER_INSTRUCTIONS if critical else REVIEWER_INSTRUCTIONS
    return (
        "---\n"
        f"description: {description}\n"
        "mode: subagent\n"
        f"model: {model}\n"
        "reasoningEffort: high\n"
        "textVerbosity: low\n"
        "permission:\n"
        "  read: allow\n"
        "  list: allow\n"
        "  glob: allow\n"
        "  grep: allow\n"
        "  edit: deny\n"
        "  write: deny\n"
        "  bash: deny\n"
        "---\n\n"
        + instructions
        + "\n"
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _patch_markdown(path: Path, content: str) -> None:
    _patch_text_block(path, START, END, content.strip() + "\n")


def _strip_managed_block(current: str, start: str, end: str) -> str:
    if start not in current or end not in current:
        return current
    prefix, tail = current.split(start, 1)
    _, suffix = tail.split(end, 1)
    return prefix.rstrip() + ("\n" if prefix.strip() and suffix.strip() else "") + suffix.lstrip("\n")


def _patch_text_block(path: Path, start: str, end: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    unmanaged = _strip_managed_block(current, start, end).rstrip()
    block = f"{start}\n{content.rstrip()}\n{end}\n"
    updated = unmanaged + ("\n\n" if unmanaged else "") + block
    path.write_text(updated, encoding="utf-8")


def _patch_codex_config(path: Path) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    unmanaged = _strip_managed_block(current, TOML_START, TOML_END)
    lines = [
        "[mcp_servers.tide]",
        'command = "tide"',
        'args = ["mcp", "serve"]',
        'default_tools_approval_mode = "auto"',
        "",
        "[mcp_servers.tide.tools.authorize]",
        'approval_mode = "prompt"',
    ]
    _patch_text_block(path, TOML_START, TOML_END, "\n".join(lines) + "\n")


def _merge_opencode(path: Path, *, bootstrap_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config: dict[str, Any]
    if path.exists():
        original = path.read_text(encoding="utf-8")
        backup = path.with_suffix(path.suffix + ".tide-backup")
        if not backup.exists():
            shutil.copy2(path, backup)
        try:
            parsed = json.loads(_normalize_jsonc(original))
        except json.JSONDecodeError as exc:
            raise TideError(
                f"cannot safely update OpenCode config {path}: {exc}. Original preserved at {backup}."
            ) from exc
        if not isinstance(parsed, dict):
            raise TideError(f"OpenCode config must contain a JSON object: {path}")
        config = parsed
    else:
        config = {}
    config.setdefault("$schema", "https://opencode.ai/config.json")
    instructions = config.get("instructions", [])
    if isinstance(instructions, str):
        instructions = [instructions]
    if not isinstance(instructions, list):
        raise TideError("OpenCode `instructions` must be a string or array")
    bootstrap = str(bootstrap_path)
    if bootstrap not in instructions:
        instructions.append(bootstrap)
    config["instructions"] = instructions
    mcp = config.setdefault("mcp", {})
    if not isinstance(mcp, dict):
        raise TideError("OpenCode `mcp` must be an object")
    mcp["tide"] = {"type": "local", "command": ["tide", "mcp", "serve"]}
    permission = config.setdefault("permission", {})
    if not isinstance(permission, dict):
        raise TideError("OpenCode `permission` must be an object")
    permission["tide_authorize"] = "ask"
    permission["tide_validate"] = "allow"
    permission["tide_validation_wait"] = "allow"
    permission["tide_commit_check"] = "allow"
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _normalize_jsonc(text: str) -> str:
    return _strip_trailing_commas(_strip_jsonc_comments(text))


def _strip_jsonc_comments(text: str) -> str:
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(text) and text[index:index + 2] != "*/":
                if text[index] in "\r\n":
                    output.append(text[index])
                index += 1
            index += 2
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _strip_trailing_commas(text: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == ",":
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead].isspace():
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                index += 1
                continue
        output.append(char)
        index += 1
    return "".join(output)
