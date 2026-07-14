from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from .locks import ModuleLock

CODE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb",
    ".php", ".cs", ".kt", ".kts", ".swift", ".c", ".cc", ".cpp", ".h",
    ".hpp", ".sql", ".sh", ".bash", ".zsh", ".fish", ".yaml", ".yml",
    ".toml", ".json",
}

DEPENDENCY_FILES = {
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "requirements-dev.txt", "requirements.in", "pipfile", "pipfile.lock",
    "poetry.lock", "uv.lock", "pdm.lock", "package.json", "package-lock.json",
    "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb", "go.mod", "go.sum",
    "cargo.toml", "cargo.lock", "gemfile", "gemfile.lock", "pom.xml",
    "build.gradle", "build.gradle.kts", "gradle.properties", "composer.json",
    "composer.lock",
}

RISK_TERMS: dict[str, tuple[str, ...]] = {
    "auth": ("auth", "autenticação", "authorization", "permission", "login", "jwt", "rbac"),
    "database": ("database", " banco ", "migration", "migração", "schema", "backfill"),
    "infrastructure": ("docker", "kubernetes", "terraform", "infrastructure", "infraestrutura", "ci/cd"),
    "public_api": ("public api", "api pública", "api contract", "contrato da api", "breaking change"),
    "dependency": ("dependency", "dependência", "package", "pacote", "library", "biblioteca", "upgrade"),
    "secrets": ("secret", "segredo", "credential", "credencial", "api key"),
    "data": ("real data", "dados reais", "reprocess", "reprocessar", "backfill"),
}


@dataclass(frozen=True)
class PolicyDecision:
    authorization_gates: tuple[str, ...]
    risk_signals: tuple[str, ...]
    review_required: bool
    review_level: str
    reasons: tuple[str, ...]
    max_writers: int = 1
    max_reviewers: int = 1

    @property
    def hardgates(self) -> tuple[str, ...]:
        """Backward-compatible alias for genuine authorization gates."""
        return self.authorization_gates


def decide(task: str, files: list[str], locks: list[ModuleLock]) -> PolicyDecision:
    lowered = f" {task.lower()} "
    authorization = _authorization_gates(lowered)
    risks = set(_text_risks(lowered)) | set(_file_risks(files))
    reasons: list[str] = []

    if locks:
        reasons.append("Module Lock applies")
    if any(lock.criticality in {"production", "critical"} for lock in locks):
        risks.add("module_contract")
        reasons.append("production/critical module")

    sensitive_terms = {
        term.lower()
        for lock in locks
        for term in lock.sensitive_changes
        if term.strip()
    }
    if any(term in lowered for term in sensitive_terms):
        risks.add("module_contract")
        reasons.append("Module Lock contract may change")

    code_change = any(_is_code_path(path) for path in files)
    review_required = code_change or bool(locks) or bool(risks)
    review_level = "critical" if locks or risks else "normal"
    if risks:
        reasons.append("technical risk requires stronger review")
    if authorization:
        reasons.append("external or irreversible action requires user authorization")

    return PolicyDecision(
        authorization_gates=tuple(sorted(authorization)),
        risk_signals=tuple(sorted(risks)),
        review_required=review_required,
        review_level=review_level,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def _authorization_gates(text: str) -> set[str]:
    gates: set[str] = set()
    production_action = re.search(
        r"\b(deploy|release|publish|apply|execute|run|implantar|publicar|aplicar|executar)\b",
        text,
    )
    production_target = re.search(r"\b(production|prod|produção)\b", text)
    if production_action and production_target:
        gates.add("production")

    if re.search(r"\b(drop|truncate|delete|wipe|purge|apagar|excluir|deletar)\b", text) and re.search(
        r"\b(data|dados|database|banco|table|tabela|rows|registros)\b", text
    ):
        gates.add("destructive_data")
    if re.search(r"\b(backfill|reprocess|reprocessar)\b", text) and re.search(
        r"\b(real|production|produção|prod)\b", text
    ):
        gates.add("destructive_data")
    if re.search(r"\b(rotate|revoke|replace|rotacionar|revogar|substituir)\b", text) and re.search(
        r"\b(secret|token|credential|api key|segredo|credencial)\b", text
    ):
        gates.add("secrets")
    if re.search(r"\b(paid|billing|charge|purchase|cost|custo|cobrança|comprar)\b", text):
        gates.add("external_cost")
    return gates


def _text_risks(text: str) -> list[str]:
    return [name for name, terms in RISK_TERMS.items() if any(term in text for term in terms)]


def _file_risks(files: list[str]) -> list[str]:
    risks: set[str] = set()
    for raw_path in files:
        path = PurePosixPath(raw_path.lower())
        name = path.name
        parts = set(path.parts)
        text = path.as_posix()
        if name in DEPENDENCY_FILES:
            risks.add("dependency")
        if name in {"dockerfile", "compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"}:
            risks.add("infrastructure")
        if ".github" in parts and "workflows" in parts:
            risks.add("infrastructure")
        if parts.intersection({"terraform", "infra", "infrastructure", "k8s", "kubernetes", "helm"}):
            risks.add("infrastructure")
        if parts.intersection({"migration", "migrations", "alembic", "prisma"}) or name.endswith(".sql"):
            risks.add("database")
        if any(fragment in text for fragment in ("auth", "permission", "permissions", "acl", "rbac")):
            risks.add("auth")
        if name.startswith(".env") or any(fragment in name for fragment in ("secret", "credential")):
            risks.add("secrets")
    return sorted(risks)


def _is_code_path(path: str) -> bool:
    pure = PurePosixPath(path.lower())
    if pure.name in DEPENDENCY_FILES:
        return True
    return pure.suffix in CODE_SUFFIXES
