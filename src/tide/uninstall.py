from __future__ import annotations
import json
import shutil
from pathlib import Path
from .project import TideError
from .setup_tools import END, START, TOML_END, TOML_START, _normalize_jsonc, _strip_managed_block

def uninstall_global(*, codex: bool, opencode: bool, remove_shared: bool=True, dry_run: bool=False) -> list[str]:
    home = Path.home()
    actions: list[str] = []
    if remove_shared:
        skill = home / '.agents' / 'skills' / 'tide'
        actions.append(f'remove skill -> {skill}')
        if not dry_run:
            shutil.rmtree(skill, ignore_errors=True)
            _remove_empty_parents(skill.parent, stop=home / '.agents')
    if codex:
        codex_dir = home / '.codex'
        agents = codex_dir / 'AGENTS.md'
        reviewer = codex_dir / 'agents' / 'tide-reviewer.toml'
        critical_reviewer = codex_dir / 'agents' / 'tide-reviewer-critical.toml'
        config = codex_dir / 'config.toml'
        actions.extend([f'remove bootstrap block -> {agents}', f'remove reviewer -> {reviewer}', f'remove critical reviewer -> {critical_reviewer}', f'remove Tide MCP block -> {config}'])
        if not dry_run:
            _remove_managed_block(agents, START, END)
            reviewer.unlink(missing_ok=True)
            critical_reviewer.unlink(missing_ok=True)
            _remove_codex_entries(config)
            _remove_empty_parents(reviewer.parent, stop=codex_dir)
    if opencode:
        config_dir = home / '.config' / 'opencode'
        agents = config_dir / 'AGENTS.md'
        reviewer = config_dir / 'agents' / 'tide-reviewer.md'
        critical_reviewer = config_dir / 'agents' / 'tide-reviewer-critical.md'
        config = config_dir / 'opencode.json'
        actions.extend([f'remove bootstrap block -> {agents}', f'remove reviewer -> {reviewer}', f'remove critical reviewer -> {critical_reviewer}', f'remove Tide entries -> {config}'])
        if not dry_run:
            _remove_managed_block(agents, START, END)
            reviewer.unlink(missing_ok=True)
            critical_reviewer.unlink(missing_ok=True)
            _remove_opencode_entries(config, bootstrap_path=agents)
            _remove_empty_parents(reviewer.parent, stop=config_dir)
    return actions

def _remove_managed_block(path: Path, start: str, end: str) -> None:
    if not path.exists():
        return
    current = path.read_text(encoding='utf-8')
    updated = _strip_managed_block(current, start, end).strip()
    if updated:
        path.write_text(updated + '\n', encoding='utf-8')
    else:
        path.unlink()

def _remove_codex_entries(path: Path) -> None:
    if not path.exists():
        return
    current = path.read_text(encoding='utf-8')
    preserved_graph = ''
    if TOML_START in current and TOML_END in current:
        _, tail = current.split(TOML_START, 1)
        managed, _ = tail.split(TOML_END, 1)
        graph_marker = '[mcp_servers.code-review-graph]'
        if graph_marker in managed:
            preserved_graph = graph_marker + managed.split(graph_marker, 1)[1].strip() + '\n'
    updated = _strip_managed_block(current, TOML_START, TOML_END).strip()
    if preserved_graph and '[mcp_servers.code-review-graph]' not in updated:
        updated = updated + ('\n\n' if updated else '') + preserved_graph.strip()
    if updated:
        path.write_text(updated + '\n', encoding='utf-8')
    else:
        path.unlink()

def _remove_opencode_entries(path: Path, *, bootstrap_path: Path) -> None:
    if not path.exists():
        return
    original = path.read_text(encoding='utf-8')
    try:
        config = json.loads(_normalize_jsonc(original))
    except json.JSONDecodeError as exc:
        raise TideError(f'cannot safely clean OpenCode config {path}: {exc}') from exc
    if not isinstance(config, dict):
        raise TideError(f'OpenCode config must contain a JSON object: {path}')
    instructions = config.get('instructions')
    bootstrap = str(bootstrap_path)
    if isinstance(instructions, str):
        if instructions == bootstrap:
            config.pop('instructions', None)
    elif isinstance(instructions, list):
        filtered = [item for item in instructions if item != bootstrap]
        if filtered:
            config['instructions'] = filtered
        else:
            config.pop('instructions', None)
    mcp = config.get('mcp')
    if isinstance(mcp, dict):
        mcp.pop('tide', None)
        if not mcp:
            config.pop('mcp', None)
    permission = config.get('permission')
    if isinstance(permission, dict):
        permission.pop('tide_authorize', None)
        permission.pop('tide_validate', None)
        if not permission:
            config.pop('permission', None)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def _remove_empty_parents(path: Path, *, stop: Path) -> None:
    current = path
    while current != stop and current.is_dir():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent
