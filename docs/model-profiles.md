# Tide Model Profiles

Este documento consolida os perfis de modelo, variant e steps para os agentes Tide.

## Perfil recomendado: balanced-quality

| Agente | Modelo | Variant | Steps | Status |
|---|---|---:|---:|---|
| `tide` | GPT-5.5 | high | 20 | pendente |
| `tide-runner` | GPT-5.5 | high | 18 | steps aplicado |
| `tide-verifier` | GPT-5.5 Fast | medium | 8 | steps aplicado |
| `tide-steward` | GPT-5.5 Fast | low/medium | 6 | steps aplicado |
| `tide-guide` | GPT-5.5 Fast | low/medium | 10 | steps aplicado |
| `tide-operator` | GPT-5.5 | medium/high | 14 | steps aplicado |
| `tide-reviewer-durability` | GPT-5.5 | high | 12 | steps aplicado |
| `tide-reviewer-simplicity` | GPT-5.5 | medium/high | 8 | steps aplicado |
| `tide-reviewer-tests` | GPT-5.5 | medium/high | 10 | pendente |
| `tide-reviewer-security` | GPT-5.5 Pro ou GPT-5.5 | xhigh | 14 | pendente |
| `tide-reviewer-data` | GPT-5.5 Pro ou GPT-5.5 | xhigh | 14 | pendente |
| `tide-reviewer-infra` | GPT-5.5 Pro ou GPT-5.5 | xhigh | 12 | pendente |

## Campos pretendidos

O OpenCode aceita configuração por agente no frontmatter. O formato exato de `model` deve ser confirmado no ambiente local antes de fixar.

Exemplo pretendido:

```yaml
---
description: Executa mudanças de código dentro da fronteira de uma Wave.
mode: subagent
model: openai/gpt-5.5
variant: high
steps: 18
permission:
  read: allow
  edit: allow
---
```

## Pendências do TIDE-0020

- Confirmar o identificador real dos modelos no arquivo de configuração do OpenCode.
- Fixar `model` e `variant` no frontmatter quando o formato estiver confirmado.
- Aplicar `steps` nos reviewers que ainda ficaram pendentes por bloqueio da ferramenta.
- Testar custo e tempo em uma sessão real após reinstall.
