from __future__ import annotations

from dataclasses import dataclass

from .locks import ModuleLock


HARDGATE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "production": ("production", "prod", "deploy"),
    "database": ("database", " banco ", " db ", "migration", "migrate"),
    "auth": ("auth", "permission", "authorization", "login", "jwt"),
    "secrets": ("secret", "token", "credential", "password", "api key"),
    "data": ("real data", "reprocess", "reprocessing", "backfill"),
    "infrastructure": ("infrastructure", "docker", "kubernetes", "ci/cd", "pipeline"),
    "public_api": ("public api", "api contract", "breaking change"),
    "dependency": ("dependency", "package", "library", "upgrade"),
}


@dataclass(frozen=True)
class PolicyDecision:
    hardgates: tuple[str, ...]
    review_required: bool
    reasons: tuple[str, ...]
    max_writers: int = 1
    max_reviewers: int = 1


def decide(task: str, files: list[str], locks: list[ModuleLock]) -> PolicyDecision:
    lowered = f" {task.lower()} "
    hardgates = [name for name, words in HARDGATE_KEYWORDS.items() if any(word in lowered for word in words)]
    reasons: list[str] = []
    review_required = False

    if locks:
        reasons.append("Module Lock applies")
    if any(lock.review_required for lock in locks):
        review_required = True
    if any(lock.criticality in {"production", "critical"} for lock in locks):
        review_required = True
        reasons.append("production/critical module")
    if hardgates:
        review_required = True
        reasons.append("sensitive change")
    if len(files) > 3:
        review_required = True
        reasons.append("change crosses more than three files")

    return PolicyDecision(
        hardgates=tuple(sorted(set(hardgates))),
        review_required=review_required,
        reasons=tuple(dict.fromkeys(reasons)),
    )
