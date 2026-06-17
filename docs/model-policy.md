# Tide Model Policy

O Tide Protocol prioriza qualidade, mas evita usar modelos fortes em tarefas mecânicas.

Modo padrão recomendado: **balanced-quality dinâmico**.

## Modelos disponíveis na configuração atual

A configuração OpenCode informada pelo supervisor mostra os seguintes modelos OpenAI disponíveis:

```txt
GPT-5.4 Fast
GPT-5.4 mini Fast
GPT-5.5
GPT-5.5 Fast
GPT-5.5 Pro
GPT-5.4 mini
GPT-5.4
GPT-5.3 Codex Spark
```

E as variantes disponíveis:

```txt
none
low
medium
high
xhigh
```

## Resposta curta

O agente deve estimar dinamicamente o **nível de esforço desejado** (`low`, `medium`, `high`, `xhigh`) com base em risco, complexidade, urgência e tipo de tarefa.

A política padrão não é perfil de instalação. É modo operacional:

```txt
balanced-quality dinâmico
```

Ou seja:

- qualidade alta por padrão em código;
- modelo/effort menor em tarefas mecânicas;
- xhigh quando o erro custa caro;
- menor número de subagentes quando o risco é baixo;
- fast mode quando o supervisor priorizar velocidade.

A troca real de modelo/effort depende do que o OpenCode permite no momento:

- se o agente/subagente já estiver pré-configurado com `model`, `variant` ou equivalente, ele usará isso;
- se não estiver, o subagente tende a herdar o modelo da sessão/agente primário;
- portanto, o Tide deve decidir o effort desejado e registrar isso no briefing ao subagente;
- a automação total de troca de modelo exige IDs reais de modelo confirmados na config do OpenCode.

## Princípios

1. Use modelo forte quando houver risco real de erro caro.
2. Use modelo médio/alto para implementação de código.
3. Use modelo leve apenas para tarefas mecânicas, leitura simples, commit e status.
4. Não economize em segurança, dados, infra e código durável sensível.
5. Limite steps para evitar loops e custo invisível.
6. Subagente só deve ser chamado quando agrega valor real.
7. Modo fast prioriza tempo de resposta, não economia financeira.

## Modo padrão: balanced-quality dinâmico

O Tide deve operar por padrão assim:

```txt
risco baixo     → fluxo enxuto, poucos subagentes, effort medium/high conforme código
risco médio     → runner/verifier + reviewer focado quando necessário
risco alto      → checkpoint prévio + reviewer especializado + effort high/xhigh
approve/reject  → steward curto, rápido e mecânico
```

## Modo fast

O supervisor pode pedir explicitamente:

```txt
modo fast
use fast
responda mais rápido
priorize velocidade
```

Quando isso acontecer, o Tide deve:

- reduzir investigação ampla;
- preferir a menor Wave segura;
- acionar menos reviewers;
- evitar análise arquitetural longa;
- usar comandos escopados antes de suites completas;
- manter hardgates: fast mode nunca autoriza produção, banco, secrets, auth, deploy ou comandos sensíveis sem checkpoint;
- aceitar gastar mais recurso/modelo rápido se isso reduzir latência;
- avisar quando fast mode reduziu profundidade de análise.

Fast mode não significa descuido. Significa:

```txt
mais direto, menos exploração, validação proporcional, hardgates preservados
```

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
- `tide`: GPT-5.5 medium;
- `tide-runner`: GPT-5.5 medium ou high quando houver código importante;
- `tide-verifier`: GPT-5.5 Fast low/medium ou GPT-5.4 Fast medium;
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
- `tide`: GPT-5.5 high;
- `tide-runner`: GPT-5.5 high quando envolver lógica de domínio, refactor relevante ou código de produção;
- `tide-reviewer-durability`: GPT-5.5 high;
- `tide-reviewer-tests`: GPT-5.5 medium/high.

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
- `tide`: GPT-5.5 high;
- `tide-runner`: GPT-5.5 Pro xhigh ou GPT-5.5 xhigh quando a implementação for sensível;
- reviewers especializados: GPT-5.5 Pro xhigh ou GPT-5.5 xhigh;
- não use modelo leve para decisões de risco.

## Matriz recomendada por agente

| Agente | Recomendação | Observação |
|---|---|---|
| `tide` | GPT-5.5 medium/high | Decide risco, fronteira e subagentes. |
| `tide-runner` | GPT-5.5 high; GPT-5.5 Pro xhigh para código crítico | Qualidade de código importa mais que economia. |
| `tide-verifier` | GPT-5.5 Fast low/medium | Mecânico, mas precisa interpretar saídas. |
| `tide-steward` | GPT-5.5 Fast low/medium | Approve/reject/commit deve ser barato e curto. |
| `tide-guide` | GPT-5.5 Fast low/medium | Dúvidas simples; subir para GPT-5.5 medium se arquitetura. |
| `tide-operator` | GPT-5.5 medium/high | Comandos de projeto podem ter risco operacional. |
| `tide-reviewer-durability` | GPT-5.5 high/xhigh | Código durável exige julgamento. |
| `tide-reviewer-simplicity` | GPT-5.5 medium/high | Julgamento de design, sem exagero. |
| `tide-reviewer-tests` | GPT-5.5 medium/high | Deve avaliar se testes provam o risco certo. |
| `tide-reviewer-security` | GPT-5.5 Pro xhigh ou GPT-5.5 xhigh | Segurança sempre prioriza qualidade. |
| `tide-reviewer-data` | GPT-5.5 Pro xhigh ou GPT-5.5 xhigh | Banco, integridade e reprocessamento são críticos. |
| `tide-reviewer-infra` | GPT-5.5 Pro xhigh ou GPT-5.5 xhigh | Infra/deploy quebram ambiente inteiro. |

## Steps aplicados

| Agente | steps |
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

Não há necessidade de perfis de instalação neste momento.

O Tide deve operar dinamicamente com `balanced-quality` por padrão. O supervisor pode pedir `modo fast` quando quiser priorizar velocidade. Modos mais específicos, como `economy`, só devem ser criados se houver necessidade real observada em uso.
