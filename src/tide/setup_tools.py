from __future__ import annotations
import json
import shutil
from importlib.resources import files
from pathlib import Path
from typing import Any
from .project import TideError
START = '<!-- tide:start -->'
END = '<!-- tide:end -->'
TOML_START = '# tide:start'
TOML_END = '# tide:end'

def setup_global(*, codex: bool, opencode: bool, dry_run: bool=False) -> list[str]:
    actions: list[str] = []
    home = Path.home()
    asset_root = files('tide').joinpath('assets')
    graph_command = shutil.which('code-review-graph')
    skill_source = asset_root.joinpath('skill')
    skill_target = home / '.agents' / 'skills' / 'tide'
    actions.append(f'install skill -> {skill_target}')
    if not dry_run:
        _copy_tree(skill_source, skill_target)
    if codex:
        codex_dir = home / '.codex'
        config_path = codex_dir / 'config.toml'
        actions.extend([f"patch bootstrap -> {codex_dir / 'AGENTS.md'}", f"install reviewer -> {codex_dir / 'agents' / 'tide-reviewer.toml'}", f"install critical reviewer -> {codex_dir / 'agents' / 'tide-reviewer-critical.toml'}", f'register Tide MCP -> {config_path}'])
        if graph_command:
            actions.append(f'register code-review-graph MCP -> {config_path}')
        if not dry_run:
            _patch_markdown(codex_dir / 'AGENTS.md', asset_root.joinpath('adapters/codex/AGENTS.md').read_text())
            _copy_file(asset_root.joinpath('adapters/codex/tide-reviewer.toml'), codex_dir / 'agents' / 'tide-reviewer.toml')
            _copy_file(asset_root.joinpath('adapters/codex/tide-reviewer-critical.toml'), codex_dir / 'agents' / 'tide-reviewer-critical.toml')
            _patch_codex_config(config_path, graph_command=graph_command)
    if opencode:
        config_dir = home / '.config' / 'opencode'
        config_path = config_dir / 'opencode.json'
        bootstrap_path = config_dir / 'AGENTS.md'
        actions.extend([f'patch bootstrap -> {bootstrap_path}', f"install reviewer -> {config_dir / 'agents' / 'tide-reviewer.md'}", f"install critical reviewer -> {config_dir / 'agents' / 'tide-reviewer-critical.md'}", f'register Tide MCP and instructions -> {config_path}'])
        if graph_command:
            actions.append(f'register code-review-graph MCP -> {config_path}')
        if not dry_run:
            _patch_markdown(bootstrap_path, asset_root.joinpath('adapters/opencode/AGENTS.md').read_text())
            _copy_file(asset_root.joinpath('adapters/opencode/tide-reviewer.md'), config_dir / 'agents' / 'tide-reviewer.md')
            _copy_file(asset_root.joinpath('adapters/opencode/tide-reviewer-critical.md'), config_dir / 'agents' / 'tide-reviewer-critical.md')
            _merge_opencode(config_path, bootstrap_path=bootstrap_path, graph_command=graph_command)
    if not graph_command:
        actions.append('code-review-graph not installed; Tide will use direct-search fallback')
    return actions

def _copy_tree(source: Any, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        destination = target / child.name
        if child.is_dir():
            _copy_tree(child, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(child.read_text(), encoding='utf-8')

def _copy_file(source: Any, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(), encoding='utf-8')

def _patch_markdown(path: Path, content: str) -> None:
    _patch_text_block(path, START, END, content.strip() + '\n')

def _strip_managed_block(current: str, start: str, end: str) -> str:
    if start not in current or end not in current:
        return current
    prefix, tail = current.split(start, 1)
    _, suffix = tail.split(end, 1)
    return prefix.rstrip() + ('\n' if prefix.strip() and suffix.strip() else '') + suffix.lstrip('\n')

def _patch_text_block(path: Path, start: str, end: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding='utf-8') if path.exists() else ''
    unmanaged = _strip_managed_block(current, start, end).rstrip()
    block = f'{start}\n{content.rstrip()}\n{end}\n'
    updated = unmanaged + ('\n\n' if unmanaged else '') + block
    path.write_text(updated, encoding='utf-8')

def _patch_codex_config(path: Path, *, graph_command: str | None) -> None:
    current = path.read_text(encoding='utf-8') if path.exists() else ''
    unmanaged = _strip_managed_block(current, TOML_START, TOML_END)
    graph_already_configured = '[mcp_servers.code-review-graph]' in unmanaged
    lines = ['[mcp_servers.tide]', 'command = "tide"', 'args = ["mcp", "serve"]', 'default_tools_approval_mode = "auto"', '', '[mcp_servers.tide.tools.authorize]', 'approval_mode = "prompt"', '', '[mcp_servers.tide.tools.validate]', 'approval_mode = "prompt"']
    if graph_command and (not graph_already_configured):
        lines.extend(['', '[mcp_servers.code-review-graph]', f'command = {json.dumps(graph_command)}', 'args = ["serve"]'])
    _patch_text_block(path, TOML_START, TOML_END, '\n'.join(lines) + '\n')

def _merge_opencode(path: Path, *, bootstrap_path: Path, graph_command: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    config: dict[str, Any]
    if path.exists():
        original = path.read_text(encoding='utf-8')
        backup = path.with_suffix(path.suffix + '.tide-backup')
        if not backup.exists():
            shutil.copy2(path, backup)
        try:
            parsed = json.loads(_normalize_jsonc(original))
        except json.JSONDecodeError as exc:
            raise TideError(f'cannot safely update OpenCode config {path}: {exc}. Original preserved at {backup}.') from exc
        if not isinstance(parsed, dict):
            raise TideError(f'OpenCode config must contain a JSON object: {path}')
        config = parsed
    else:
        config = {}
    config.setdefault('$schema', 'https://opencode.ai/config.json')
    instructions = config.get('instructions', [])
    if isinstance(instructions, str):
        instructions = [instructions]
    if not isinstance(instructions, list):
        raise TideError('OpenCode `instructions` must be a string or array')
    bootstrap = str(bootstrap_path)
    if bootstrap not in instructions:
        instructions.append(bootstrap)
    config['instructions'] = instructions
    mcp = config.setdefault('mcp', {})
    if not isinstance(mcp, dict):
        raise TideError('OpenCode `mcp` must be an object')
    mcp['tide'] = {'type': 'local', 'command': ['tide', 'mcp', 'serve']}
    if graph_command and 'code-review-graph' not in mcp:
        mcp['code-review-graph'] = {'type': 'local', 'command': [graph_command, 'serve']}
    permission = config.setdefault('permission', {})
    if not isinstance(permission, dict):
        raise TideError('OpenCode `permission` must be an object')
    permission['tide_authorize'] = 'ask'
    permission['tide_validate'] = 'ask'
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def _normalize_jsonc(text: str) -> str:
    without_comments = _strip_jsonc_comments(text)
    return _strip_trailing_commas(without_comments)

def _strip_jsonc_comments(text: str) -> str:
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ''
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == '\\':
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
        if char == '/' and next_char == '/':
            index += 2
            while index < len(text) and text[index] not in '\r\n':
                index += 1
            continue
        if char == '/' and next_char == '*':
            index += 2
            while index + 1 < len(text) and text[index:index + 2] != '*/':
                if text[index] in '\r\n':
                    output.append(text[index])
                index += 1
            index += 2
            continue
        output.append(char)
        index += 1
    return ''.join(output)

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
            elif char == '\\':
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
        if char == ',':
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead].isspace():
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in '}]':
                index += 1
                continue
        output.append(char)
        index += 1
    return ''.join(output)
