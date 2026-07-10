from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from .locks import ModuleLock


HARDGATE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "production": ("production", "produção", "deploy", "implantar"),
    "database": ("database", " banco ", " db ", "migration", "migrate", "migração"),
    "auth": ("auth", "autenticação", "permission", "permissão", "authorization", "login", "jwt"),
    "secrets": ("secret", "segredo", "token", "credential", "credencial", "password", "senha", "api key"),
    "data": ("real data", "dados reais", "reprocess", "reprocessar", "reprocessing", "backfill"),
    "infrastructure": ("infrastructure", "infraestrutura", "docker", "kubernetes", "ci/cd", "pipeline"),
    "public_api": ("public api", "api pública", "api contract", "contrato da api", "breaking change"),
    "dependency": ("dependency", "dependência", "package", "pacote", "library", "biblioteca", "upgrade", "install"),
}

DEPENDENCY_FILES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.in",
    "pipfile",
    "pipfile.lock",
    "poetry.lock",
    "uv.lock",
    "pdm.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "go.mod",
    "go.sum",
    "cargo.toml",
    "cargo.lock",
    "gemfile",
    "gemfile.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "gradle.properties",
    "composer.json",
    "composer.lock",
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
    hardgates = [
        name
        for name, words in HARDGATE_KEYWORDS.items()
        if any(word in lowered for word in words)
    ]
    hardgates.extend(_file_hardgates(files))
    reasons: list[str] = []
    review_required = False

    if locks:
        reasons.append("Module Lock applies")
    if any(lock.review_required for lock in locks):
        review_required = True
    if any(lock.criticality in {"production", "critical"} for lock in locks):
        review_required = True
        reasons.append("production/critical module")

    sensitive_terms = {
        term.lower()
        for lock in locks
        for term in lock.sensitive_changes
        if term.strip()
    }
    if any(term in lowered for term in sensitive_terms):
        hardgates.append("module_contract")
        review_required = True
        reasons.append("Module Lock contract may change")

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


def _file_hardgates(files: list[str]) -> list[str]:
    gates: set[str] = set()
    for raw_path in files:
        path = PurePosixPath(raw_path.lower())
        name = path.name
        parts = set(path.parts)
        text = path.as_posix()
        if name in DEPENDENCY_FILES:
            gates.add("dependency")
        if name in {"dockerfile", "compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"}:
            gates.add("infrastructure")
        if ".github" in parts and "workflows" in parts:
            gates.add("infrastructure")
        if parts.intersection({"terraform", "infra", "infrastructure", "k8s", "kubernetes", "helm"}):
            gates.add("infrastructure")
        if parts.intersection({"migration", "migrations", "alembic", "prisma"}) or name.endswith(".sql"):
            gates.add("database")
        if any(fragment in text for fragment in ("auth", "permission", "permissions", "acl", "rbac")):
            gates.add("auth")
        if name.startswith(".env") or any(fragment in name for fragment in ("secret", "credential")):
            gates.add("secrets")
    return sorted(gates)
