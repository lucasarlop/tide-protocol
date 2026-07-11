from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .project import TideError


@dataclass(frozen=True)
class ModuleLock:
    file: Path
    name: str
    paths: tuple[str, ...]
    criticality: str
    review_required: bool
    validations: tuple[str, ...]
    invariants: tuple[str, ...]
    sensitive_changes: tuple[str, ...]
    body: str

    def matches(self, path: str) -> bool:
        normalized = Path(path).as_posix()
        return any(_matches(normalized, pattern) for pattern in self.paths)


def _matches(path: str, pattern: str) -> bool:
    normalized = pattern.rstrip("/")
    if normalized.endswith("/**"):
        prefix = normalized[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatch(path, normalized) or path == normalized


def parse_lock(path: Path) -> ModuleLock:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("+++\n"):
        raise TideError(f"invalid Module Lock front matter: {path}")
    try:
        raw_meta, body = text[4:].split("\n+++\n", 1)
    except ValueError as exc:
        raise TideError(f"unclosed Module Lock front matter: {path}") from exc
    try:
        meta: dict[str, Any] = tomllib.loads(raw_meta)
    except tomllib.TOMLDecodeError as exc:
        raise TideError(f"invalid Module Lock TOML in {path}: {exc}") from exc

    name = str(meta.get("name") or path.stem)
    paths = tuple(str(item) for item in meta.get("paths", []))
    if not paths:
        raise TideError(f"Module Lock has no paths: {path}")
    return ModuleLock(
        file=path,
        name=name,
        paths=paths,
        criticality=str(meta.get("criticality", "standard")),
        review_required=bool(meta.get("review_required", True)),
        validations=tuple(str(item) for item in meta.get("validations", [])),
        invariants=tuple(str(item) for item in meta.get("invariants", [])),
        sensitive_changes=tuple(str(item) for item in meta.get("sensitive_changes", [])),
        body=body.strip(),
    )


def lock_dir(root: Path) -> Path:
    return root / ".tide" / "locks"


def load_locks(root: Path) -> list[ModuleLock]:
    directory = lock_dir(root)
    if not directory.exists():
        return []
    locks: list[ModuleLock] = []
    for path in sorted(directory.glob("*.md")):
        locks.append(parse_lock(path))
    return locks


def matching_locks(root: Path, files: list[str]) -> list[ModuleLock]:
    matches: list[ModuleLock] = []
    for lock in load_locks(root):
        if any(_lock_applies(lock, path) for path in files):
            matches.append(lock)
    return matches


def _lock_applies(lock: ModuleLock, path_or_pattern: str) -> bool:
    if not any(char in path_or_pattern for char in "*?["):
        return lock.matches(path_or_pattern)
    candidate_prefix = _static_prefix(path_or_pattern)
    return any(
        _prefixes_overlap(candidate_prefix, _static_prefix(pattern))
        for pattern in lock.paths
    )


def _static_prefix(pattern: str) -> str:
    parts: list[str] = []
    for part in Path(pattern).as_posix().split("/"):
        if any(char in part for char in "*?["):
            break
        if part:
            parts.append(part)
    return "/".join(parts)


def _prefixes_overlap(left: str, right: str) -> bool:
    if not left or not right:
        return True
    return (
        left == right
        or left.startswith(right.rstrip("/") + "/")
        or right.startswith(left.rstrip("/") + "/")
    )


def render_draft(*, name: str, scope: str, criticality: str = "production") -> str:
    scope = Path(scope).as_posix().rstrip("/")
    return f'''+++
name = "{name}"
paths = ["{scope}/**"]
criticality = "{criticality}"
review_required = true
validations = []
invariants = []
sensitive_changes = []
+++
# {name}

## Responsibility

Describe only the stable responsibility of this module.

## Contracts

Record contracts that are expensive or unsafe to rediscover.

## Operational notes

Keep this short. Do not document code that is obvious from reading the implementation.
'''
