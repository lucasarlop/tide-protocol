from __future__ import annotations

import json
from typing import Any


LABELS = {
    "version": "Versão",
    "python": "Python",
    "tide_command": "Comando",
    "project": "Projeto",
    "project_warning": "Aviso",
    "runtime": "Runtime",
    "locks": "Module Locks",
    "context": "Contexto",
    "task": "Tarefa",
    "status": "Status",
    "revision": "Revisão",
    "boundary": "Fronteira",
    "boundary_required": "Fronteira necessária",
    "preexisting_changes": "Alterações pré-existentes",
    "hardgates": "Hardgates",
    "authorized_hardgates": "Hardgates autorizados",
    "pending_hardgates": "Hardgates pendentes",
    "mutation_allowed": "Edição permitida",
    "review_required": "Review necessária",
    "review_reasons": "Motivos da review",
    "required_validations": "Validações obrigatórias",
    "rules": "Regras",
    "writers": "Escritores",
    "reviewers": "Reviewers",
    "commit_requires_supervisor": "Commit exige supervisor",
    "ready": "Pronto",
    "files": "Arquivos da tarefa",
    "all_worktree_changes": "Alterações no working tree",
    "outside_boundary": "Fora da fronteira",
    "missing_validations": "Validações ausentes",
    "current_validation_count": "Validações atuais",
    "stale_validation_count": "Validações obsoletas",
    "failed_validation_count": "Validações com falha",
    "review_current": "Review atual",
    "review": "Review",
    "review_id": "Review ID",
    "resource": "Recurso",
    "review_focus": "Foco da review",
    "validation_count": "Validações",
    "diff_bytes": "Tamanho do diff",
    "diff_truncated": "Diff truncado",
    "blockers": "Bloqueios",
    "passed": "Passou",
    "command": "Comando",
    "exit_code": "Código de saída",
    "timed_out": "Timeout",
    "duration_seconds": "Duração",
    "log_id": "Log ID",
    "log_path": "Log",
    "stdout_tail": "Últimas linhas da saída",
    "stderr_tail": "Últimas linhas de erro",
    "stdout_bytes": "Bytes de saída",
    "stderr_bytes": "Bytes de erro",
    "content": "Conteúdo",
    "approved": "Aprovada",
    "findings": "Achados",
    "actions": "Ações",
    "dry_run": "Simulação",
    "created": "Criado",
    "valid": "Válido",
    "name": "Nome",
    "paths": "Caminhos",
    "criticality": "Criticidade",
    "invariants": "Invariantes",
    "validations": "Validações",
    "sensitive_changes": "Mudanças sensíveis",
    "query": "Consulta",
    "truth": "Fonte da verdade",
    "graph": "Code review graph",
    "available": "Disponível",
    "index_exists": "Índice existente",
    "executable": "Executável",
    "mcp_command": "Comando MCP",
    "direct_search": "Resultados diretos",
    "context_quality": "Qualidade do contexto",
    "recommended_sequence": "Sequência recomendada",
    "instruction": "Instrução",
    "updated": "Atualizado",
    "uninstalled": "Desinstalado",
    "adapters": "Adapters",
    "tool_removed": "Pacote removido",
    "shared_removed": "Skill compartilhada removida",
    "setup_command": "Comando de reconfiguração",
    "uv_output": "Saída do uv",
}

VALUE_TRANSLATIONS = {
    "no active Tide preparation": "nenhum preparo ativo",
    "no boundary declared": "nenhuma fronteira declarada",
    "files changed outside the declared boundary": "há arquivos alterados fora da fronteira",
    "hardgates not authorized": "há hardgates sem autorização",
    "no validation recorded for the current diff": "nenhuma validação registrada para o diff atual",
    "one or more validations failed for the current diff": "uma ou mais validações falharam no diff atual",
    "Module Lock validations are missing for the current diff": "faltam validações obrigatórias do Module Lock",
    "independent review required": "review independente obrigatória",
    "independent review is stale for the current diff": "a review independente está obsoleta para o diff atual",
    "independent review has blocking findings": "a review independente encontrou bloqueios",
}

STATUS = {
    "prepared": "preparado",
    "revising": "em revisão",
    "ready": "pronto",
    "blocked": "bloqueado",
}


def emit(value: object, *, as_json: bool = False, title: str | None = None) -> None:
    if as_json:
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return
    lines = render(value, title=title)
    print("\n".join(lines))


def render(value: object, *, title: str | None = None) -> list[str]:
    lines: list[str] = []
    if title:
        lines.append(title)
    lines.extend(_render_value(value, level=0))
    return lines or ["Nenhum dado."]


def _render_value(value: object, *, level: int, key: str | None = None) -> list[str]:
    prefix = "  " * level
    label = _label(key) if key else None
    if isinstance(value, dict):
        lines: list[str] = []
        if label:
            lines.append(f"{prefix}{label}:")
            level += 1
            prefix = "  " * level
        simple = [(k, v) for k, v in value.items() if _is_simple(v)]
        complex_items = [(k, v) for k, v in value.items() if not _is_simple(v)]
        for item_key, item_value in simple:
            if item_value is None or item_value == "":
                continue
            formatted = _format_scalar(item_key, item_value)
            if isinstance(formatted, str) and "\n" in formatted:
                lines.append(f"{prefix}{_label(item_key)}:")
                lines.extend(f"{prefix}  {line}" for line in formatted.splitlines())
            else:
                lines.append(f"{prefix}{_label(item_key)}: {formatted}")
        for item_key, item_value in complex_items:
            if item_value in (None, [], {}):
                continue
            lines.extend(_render_value(item_value, level=level, key=item_key))
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{prefix}{label}: nenhum"] if label else []
        lines = [f"{prefix}{label}:" if label else f"{prefix}-"]
        item_level = level + 1 if label else level
        for item in value:
            item_prefix = "  " * item_level
            if isinstance(item, dict):
                heading = _dict_heading(item)
                if heading:
                    lines.append(f"{item_prefix}- {heading}")
                    remainder = {k: v for k, v in item.items() if k not in {"name", "title", "path", "file"}}
                    lines.extend(_render_value(remainder, level=item_level + 1))
                else:
                    lines.append(f"{item_prefix}-")
                    lines.extend(_render_value(item, level=item_level + 1))
            else:
                lines.append(f"{item_prefix}- {_format_scalar(key, item)}")
        return lines
    if label:
        return [f"{prefix}{label}: {_format_scalar(key, value)}"]
    return [f"{prefix}{_format_scalar(key, value)}"]


def _dict_heading(value: dict[str, Any]) -> str | None:
    for key in ("name", "title", "path", "file", "review_id", "log_id"):
        item = value.get(key)
        if item:
            return str(item)
    return None


def _label(key: str | None) -> str:
    if not key:
        return ""
    return LABELS.get(key, key.replace("_", " ").capitalize())


def _is_simple(value: object) -> bool:
    return not isinstance(value, (dict, list))


def _format_scalar(key: str | None, value: object) -> str:
    if isinstance(value, bool):
        return "sim" if value else "não"
    if key == "status" and isinstance(value, str):
        return STATUS.get(value, value)
    if key == "duration_seconds" and isinstance(value, (int, float)):
        return f"{value:.2f}s"
    if key in {"diff_bytes", "stdout_bytes", "stderr_bytes"} and isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    if isinstance(value, str):
        return VALUE_TRANSLATIONS.get(value, value)
    return str(value)
