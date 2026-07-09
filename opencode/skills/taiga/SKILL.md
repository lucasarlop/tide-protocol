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
  --tag airflow \
  --description-stdin \
  --dry-run <<'EOF'
Descrição no padrão do time.
EOF
```

Depois da aprovação explícita, repita com `--yes` e sem `--dry-run`.

Criação de Task vinculada a uma User Story:

```bash
tide taiga create \
  --kind task \
  --userstory-ref 798 \
  --subject "Título da subtarefa" \
  --status doing \
  --due-date today \
  --description-stdin \
  --dry-run <<'EOF'
Descrição curta da subtarefa.
EOF
```

## Padrão de descrição para cards

Prefira o padrão curto usado pelo time:

```md
EU quero <registrar/fazer/ajustar algo>.
COMO <papel/time/responsável pelo domínio>.
PARA QUE <resultado esperado/valor para o negócio>.

Resumo do que será feito:

- item objetivo 1
- item objetivo 2
- item objetivo 3

Pendências operacionais:

- pendência 1
- pendência 2

<link relevante, se existir>
```

Para trabalho ainda não executado, use “Resumo do que será feito”. Para trabalho já concluído, use “Resumo do que foi feito”.

## Gestão do card

Padrões ao criar:

- tipo padrão: `userstory`;
- responsável padrão: usuário atual do Taiga;
- status padrão: alias `doing`, se existir no projeto;
- data padrão: hoje;
- tags: preferir tags existentes, usando `tide taiga tags` e `tide taiga suggest-tags`.

Se o status `doing` não existir, o CLI não força status default. Consulte `statuses` e proponha uma alternativa.

## Escrita e confirmação

Escritas sensíveis exigem confirmação explícita:

- criar item;
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
