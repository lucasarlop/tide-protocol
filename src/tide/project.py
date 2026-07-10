from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


DIFF_LIMIT = 120_000


class TideError(RuntimeError):
    pass


def run_git(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
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
    index = 0
    while index < len(items):
        item = items[index]
        if not item:
            index += 1
            continue
        status = item[:2]
        payload = item[3:] if len(item) >= 4 else ""
        if payload:
            paths.add(Path(payload).as_posix())
        # In porcelain -z, rename/copy records are followed by the original path.
        if "R" in status or "C" in status:
            index += 2
        else:
            index += 1
    return sorted(paths)


def staged_files(root: Path) -> list[str]:
    result = run_git(["diff", "--cached", "--name-only", "-z"], cwd=root)
    return sorted(path for path in result.stdout.split("\0") if path)


def current_diff(root: Path, paths: list[str] | None = None) -> dict[str, Any]:
    selected = paths or changed_files(root)
    tracked: list[str] = []
    untracked: list[str] = []
    for path in selected:
        result = run_git(["ls-files", "--error-unmatch", "--", path], cwd=root, check=False)
        (tracked if result.returncode == 0 else untracked).append(path)

    parts: list[str] = []
    if tracked:
        result = run_git(["diff", "--no-ext-diff", "--binary", "HEAD", "--", *tracked], cwd=root)
        parts.append(result.stdout)
    for path in untracked:
        result = subprocess.run(
            ["git", "diff", "--no-index", "--binary", "--", "/dev/null", path],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if result.returncode not in {0, 1}:
            raise TideError(result.stderr.strip() or f"cannot build diff for {path}")
        parts.append(result.stdout)

    full_text = "".join(parts)
    text = full_text
    truncated = len(text) > DIFF_LIMIT
    if truncated:
        text = text[:DIFF_LIMIT] + "\n...[diff truncated by Tide]"
    return {"text": text, "truncated": truncated, "bytes": len(full_text.encode("utf-8"))}
