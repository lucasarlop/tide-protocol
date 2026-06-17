# Tide Model Policy

O Tide Protocol prioriza qualidade, mas evita usar modelos fortes em tarefas mecânicas.

Perfil recomendado para Lucas: **balanced-quality**.

## Resposta curta

O agente pode estimar dinamicamente o **nível de esforço desejado** (`medium`, `high`, `xhigh`) com base em risco, complexidade e tipo de tarefa.

Mas a troca real de modelo/effort depende do que o OpenCode permite no momento:

- se o agente/subagente já estiver pré-configurado com `model`, `variant` ou equivalente, ele usará isso;
- se não estiver, o subagente tende a herdar o modelo da sessão/agente primário;
- portanto, o Tide deve decidir o effort desejado e rotear para o subagente/perfil adequado;
- a automação total de troca de modelo exige perfis ou agentes pré-configurados.

## Princípios

1. Use modelo forte quando houver risco real de erro caro.
2. Use modelo médio/alto para implementação de código.
3. Use modelo leve apenas para tarefas mecânicas, leitura simples, commit e status.
4. Não economize em segurança, dados, infra e código durável sensível.
5. Limite steps para evitar loops e custo invisível.
6. Subagente só deve ser chamado quando agrega valor real.

## Política por risco

### Baixo risco

Exemplos:
- bug pequeno;
- poucos arquivos;
- sem banco, auth, infra ou API pública;
- validação conhecida.

Fluxo:

```txt
tide → tide-runner → tide-verifier → checkpoint
```

Modelo/effort desejado:
- `tide`: medium;
- `tide-runner`: medium ou high quando houver código importante;
- `tide-verifier`: low/medium;
- sem reviewer por padrão.

### Médio risco

Exemplos:
- comportamento relevante;
- validação não trivial;
- mais de um módulo;
- durabilidade importante.

Fluxo:

```txt
tide → tide-runner → tide-verifier → 0-1 reviewer focado → checkpoint
```

Modelo/effort desejado:
- `tide`: medium/high;
- `tide-runner`: high quando envolver lógica de domínio, refactor relevante ou código de produção;
- `tide-reviewer-durability`: high quando a mudança afeta operação futura;
- `tide-reviewer-tests`: medium/high.

### Alto risco

Exemplos:
- segurança;
- permissões;
- tokens;
- banco;
- migração;
- reprocessamento;
- produção;
- SSH;
- deploy;
- CI/CD;
- API pública;
- nova dependência.

Fluxo:

```txt
tide → checkpoint prévio → runner/operator → verifier → reviewer especializado → checkpoint
```

Modelo/effort desejado:
- use high/xhigh nos reviewers especializados;
- use high/xhigh no runner quando a implementação for sensível;
- use medium/high no orquestrador;
- não use modelo leve para decisões de risco.

## Matriz recomendada por agente

| Agente | Recomendação | Observação |
|---|---|---|
| `tide` | medium/high | Decide risco, fronteira e subagentes. |
| `tide-runner` | high para código; xhigh para código crítico | Qualidade de código importa mais que economia. |
| `tide-verifier` | low/medium | Mecânico, mas precisa interpretar saídas. |
| `tide-steward` | low/medium | Approve/reject/commit deve ser barato e curto. |
| `tide-guide` | low/medium | Dúvidas simples; subir para medium se arquitetura. |
| `tide-operator` | medium/high | Comandos de projeto podem ter risco operacional. |
| `tide-reviewer-durability` | high/xhigh | Código durável exige julgamento. |
| `tide-reviewer-simplicity` | medium/high | Julgamento de design, sem exagero. |
| `tide-reviewer-tests` | medium/high | Deve avaliar se testes provam o risco certo. |
| `tide-reviewer-security` | high/xhigh | Segurança sempre prioriza qualidade. |
| `tide-reviewer-data` | high/xhigh | Banco, integridade e reprocessamento são críticos. |
| `tide-reviewer-infra` | high/xhigh | Infra/deploy quebram ambiente inteiro. |

## Steps recomendados

| Agente | steps sugerido |
|---|---:|
| `tide` | 20 |
| `tide-runner` | 18 |
| `tide-verifier` | 8 |
| `tide-steward` | 6 |
| `tide-guide` | 10 |
| `tide-operator` | 14 |
| `tide-reviewer-durability` | 12 |
| `tide-reviewer-simplicity` | 8 |
| `tide-reviewer-tests` | 10 |
| `tide-reviewer-security` | 14 |
| `tide-reviewer-data` | 14 |
| `tide-reviewer-infra` | 12 |

## Regras para reduzir custo sem perder qualidade

- Não chame reviewer em baixo risco, salvo sinal real de risco.
- Não use subagente só para repetir análise já feita.
- `tide-steward` deve ser direto: status, commit/reject, working tree e resultado.
- Validação executável deve preferir `tide run` ou `tide project run`.
- Depois de `validated`, não chame `tide wave park` novamente.
- Checkpoint final deve consultar estado real da Wave antes de resumir.

## Configuração futura

O Tide deve oferecer perfis:

```txt
balanced-quality  padrão recomendado
quality           usa high/xhigh em runner/reviewers com mais frequência
economy           reduz reviewers e usa modelos menores em tarefas mecânicas
```

Para Lucas, o perfil recomendado é `balanced-quality`, com inclinação para `quality` em código de produção, dados, segurança, infra e bibliotecas compartilhadas.
