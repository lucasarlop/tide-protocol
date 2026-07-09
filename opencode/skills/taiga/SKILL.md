---
name: taiga
description: Integração opcional com Taiga para criar, vincular, avaliar e sincronizar atividades organizacionais com Waves Tide.
license: MIT
compatibility: opencode
---

# taiga

Use esta skill somente quando o supervisor sinalizar Taiga explicitamente ou quando a Wave já estiver vinculada ao Taiga.

Taiga não é default do Tide. É uma integração opcional.

## Modelo atual

Use User Story como item padrão de gestão/board. Use Task apenas quando o supervisor pedir subtarefas ou quando houver uma User Story explícita para vincular.

Não coloque `Wave: TIDE-XXXX`, tag `tide` ou tag `TIDE-XXXX` na descrição pública do Taiga por padrão. O vínculo com Wave fica no metadado local.

## Configuração

Configure localmente com:

```bash
tide taiga configure --default-kind userstory
```

Campos mínimos:

```txt
base_url: URL base da API Taiga, ex: https://taiga.example/api/v1
project_id: ID numérico do projeto
default_kind: userstory | task | issue
auth_token: token de acesso
```

A configuração não sensível fica em:

```txt
~/.config/tide/taiga/config.json
```

O token deve ser salvo no macOS Keychain quando disponível. Fallback local só deve ser usado com `--allow-local-token`, nunca em `.env` do projeto.

## Regra obrigatória antes de escrever

Antes de qualquer alteração real no Taiga, mostre exatamente o que será alterado e aguarde autorização ou ajuste do supervisor.

Fluxo obrigatório:

1. rode o comando com `--dry-run`;
2. mostre o plano ao supervisor em formato legível;
3. aguarde aprovação explícita ou ajuste;
4. só depois rode o mesmo comando com `--yes` e sem `--dry-run`.

Não pule o preview mesmo quando a Wave já estiver vinculada ao Taiga.

## Comandos de descoberta

Antes de criar ou atualizar cards, consulte contexto do projeto:

```bash
tide taiga whoami
tide taiga statuses --kind userstory
tide taiga statuses --kind task
tide taiga members
tide taiga tags
tide taiga suggest-tags --subject "Título" --text-stdin
```

Use `statuses` para mapear `doing`, `done` ou um status explícito para os nomes reais do projeto. Use `tags` e `suggest-tags` para preferir tags já existentes.

## Comandos operacionais

Read-only:

```bash
tide taiga projects
tide taiga list --kind userstory
tide taiga find --kind userstory --contains "termo"
tide taiga get --kind userstory --ref 231
tide taiga maturity --kind userstory --ref 231
```

Preview de criação de User Story no board:

```bash
tide taiga create \
  --kind userstory \
  --subject "Título" \
  --status doing \
  --due-date today \
  --tag dados \
  --description-stdin \
  --dry-run <<'EOF'
**EU QUERO** [...]
**COMO** [...]
**PARA QUE** [...]

**Escopo**

- item necessário

**Fora do Escopo**

- item necessário
EOF
```

Depois da aprovação explícita, repita com `--yes` e sem `--dry-run`.

Criação de Tasks vinculadas à User Story, em lote:

```bash
tide taiga create-tasks \
  --userstory-ref 819 \
  --status doing \
  --due-date today \
  --tasks-stdin \
  --dry-run <<'EOF'
Criar script ValidatePessoas.py | Critério: script criado e executável em ambiente aprovado.
Integrar validação pós-Keycloak | Critério: DAG chama validação no checkpoint correto.
Integrar validação final | Critério: DAG chama validação final após enriquecimentos.
EOF
```

Depois da aprovação explícita, repita com `--yes`.

## Padrão de descrição para cards

Use descrição MUITO simples:

```md
**EU QUERO** [...]
**COMO** [...]
**PARA QUE** [...]

**Escopo**

- somente se necessário

**Fora do Escopo**

- somente se necessário

[link para commit no GitLab apenas quando a tarefa estiver concluída]
[resumo com principais considerações apenas quando a tarefa estiver concluída]
```

Não use diagnóstico longo, lista extensa de evidências, critérios de aceite detalhados, tarefas técnicas completas ou relatório da Wave na descrição inicial do card. Isso deve ficar no contexto local da Wave ou em comentário posterior, se aprovado.

## Gestão do card

Padrões ao criar:

- tipo padrão: `userstory`;
- responsável padrão: usuário atual do Taiga;
- status padrão: alias `doing`, se existir no projeto;
- data padrão: hoje;
- tags: preferir tags existentes, usando `tide taiga tags` e `tide taiga suggest-tags`.

Se o status `doing` não existir, o CLI não força status default. Consulte `statuses` e proponha uma alternativa.

Para toda User Story com trabalho decomponível, crie também Tasks vinculadas usando `tide taiga create-tasks`. Não deixe a seção Tasks vazia quando o planejamento já tiver passos claros.

## Escrita e confirmação

Escritas sensíveis exigem confirmação explícita:

- criar item;
- criar tasks vinculadas;
- editar descrição;
- mover status;
- trocar assignee;
- trocar sprint;
- atualizar campos organizacionais.

Comentar progresso/fechamento pode ser automático somente depois de preview aprovado.

## Segurança

- Nunca exponha token.
- Nunca leia token/config diretamente fora do CLI.
- Nunca importe `tide-taiga` como módulo Python.
- Não crie scripts/código ad-hoc para falar com Taiga.
- Use ref visível (`#231`) quando existir, não ID interno.
- Confirme membros/status antes de atribuir ou mover.
- Não acople Taiga a órgão, empresa ou projeto específico.
- Não execute remoções pelo agente.
