from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class TideError(RuntimeError):
    pass


def run_git(args: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise TideError(message)
    return result


def project_root(cwd: Path | None = None) -> Path:
    base = (cwd or Path.cwd()).resolve()
    result = run_git(["rev-parse", "--show-toplevel"], cwd=base, check=False)
    if result.returncode != 0:
        raise TideError("run Tide inside a Git repository")
    return Path(result.stdout.strip()).resolve()


def git_dir(root: Path) -> Path:
    result = run_git(["rev-parse", "--git-dir"], cwd=root)
    path = Path(result.stdout.strip())
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def runtime_dir(root: Path) -> Path:
    directory = git_dir(root) / "tide"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def runtime_path(root: Path) -> Path:
    return runtime_dir(root) / "current.json"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_runtime(root: Path) -> dict[str, Any]:
    return read_json(runtime_path(root), {})


def save_runtime(root: Path, value: dict[str, Any]) -> None:
    write_json(runtime_path(root), value)


def changed_files(root: Path) -> list[str]:
    result = run_git(["status", "--porcelain=v1", "-z"], cwd=root)
    items = result.stdout.split("\0")
    paths: set[str] = set()
    for item in items:
        if not item:
            continue
        payload = item[3:] if len(item) >= 4 else item
        if " -> " in payload:
            payload = payload.split(" -> ", 1)[1]
        if payload:
            paths.add(Path(payload).as_posix())
    return sorted(paths)


def staged_files(root: Path) -> list[str]:
    result = run_git(["diff", "--cached", "--name-only", "-z"], cwd=root)
    return sorted(path for path in result.stdout.split("\0") if path)
