from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .project import TideError
from .uninstall import uninstall_global


PACKAGE_NAME = "tide-protocol"


def detect_adapters(home: Path | None = None) -> dict[str, bool]:
    home = home or Path.home()
    codex = _contains(home / ".codex" / "AGENTS.md", "<!-- tide:start -->") or (
        home / ".codex" / "agents" / "tide-reviewer.toml"
    ).exists()
    opencode = _contains(
        home / ".config" / "opencode" / "AGENTS.md", "<!-- tide:start -->"
    ) or (
        home / ".config" / "opencode" / "agents" / "tide-reviewer.md"
    ).exists()
    return {"codex": codex, "opencode": opencode}


def update_tool(*, dry_run: bool = False) -> dict[str, Any]:
    uv = shutil.which("uv")
    if not uv:
        raise TideError("uv not found; install it before running tide update")

    adapters = detect_adapters()
    command = [uv, "tool", "upgrade", "--reinstall", PACKAGE_NAME]
    if dry_run:
        return {
            "updated": False,
            "dry_run": True,
            "command": command,
            "adapters": _enabled_adapters(adapters),
        }

    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "uv tool upgrade failed").strip()
        raise TideError(detail)

    enabled = _enabled_adapters(adapters)
    setup_actions: list[str] = []
    setup_command: list[str] | None = None
    if enabled:
        tide = shutil.which("tide") or "tide"
        setup_command = [tide, "setup", "--json"]
        if adapters["codex"]:
            setup_command.append("--codex")
        if adapters["opencode"]:
            setup_command.append("--opencode")

        setup_result = subprocess.run(setup_command, text=True, capture_output=True)
        if setup_result.returncode != 0:
            detail = (
                setup_result.stderr
                or setup_result.stdout
                or "tide setup failed after update"
            ).strip()
            raise TideError(detail)
        try:
            setup_payload = json.loads(setup_result.stdout)
            setup_actions = list(setup_payload.get("actions", []))
        except (ValueError, TypeError):
            if setup_result.stdout.strip():
                setup_actions = [setup_result.stdout.strip()]

    return {
        "updated": True,
        "command": command,
        "adapters": enabled,
        "setup_command": setup_command,
        "actions": setup_actions,
        "uv_output": (result.stdout or result.stderr or "").strip(),
    }


def uninstall_tool(
    *,
    codex: bool,
    opencode: bool,
    dry_run: bool = False,
    remove_package: bool = True,
    remove_shared: bool = True,
) -> dict[str, Any]:
    actions = uninstall_global(
        codex=codex,
        opencode=opencode,
        remove_shared=remove_shared,
        dry_run=dry_run,
    )
    uv = shutil.which("uv")
    command = [uv, "tool", "uninstall", PACKAGE_NAME] if uv else None

    if remove_package:
        if not uv:
            raise TideError(
                "uv not found; global integrations were removed, "
                "but the package remains installed"
            )
        if not dry_run:
            result = subprocess.run(command, text=True, capture_output=True)
            if result.returncode != 0:
                detail = (
                    result.stderr or result.stdout or "uv tool uninstall failed"
                ).strip()
                raise TideError(detail)

    adapters = {"codex": codex, "opencode": opencode}
    return {
        "uninstalled": not dry_run,
        "dry_run": dry_run,
        "adapters": _enabled_adapters(adapters),
        "actions": actions,
        "tool_removed": bool(remove_package and not dry_run),
        "shared_removed": bool(remove_shared and not dry_run),
        "command": command,
    }


def _enabled_adapters(adapters: dict[str, bool]) -> list[str]:
    return [name for name, enabled in adapters.items() if enabled]


def _contains(path: Path, marker: str) -> bool:
    try:
        return marker in path.read_text(encoding="utf-8")
    except OSError:
        return False
