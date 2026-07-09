---
name: taiga
description: Integração opcional com Taiga para criar, vincular, avaliar e sincronizar atividades organizacionais com Waves Tide.
license: MIT
compatibility: opencode
---

# taiga

Use esta skill somente quando o supervisor sinalizar Taiga explicitamente ou quando a Wave já estiver vinculada ao Taiga.

Taiga não é default do Tide. É uma integração opcional.

## Configuração

Configure localmente com:

```bash
tide taiga configure
```

Campos mínimos:

```txt
base_url: URL base da API Taiga, ex: https://taiga.example/api/v1
project_id: ID numérico do projeto
default_kind: task | userstory | issue
auth_token: token de acesso
```

A configuração não sensível fica em:

```txt
~/.config/tide/taiga/config.json
```

O token deve ser salvo no macOS Keychain quando disponível. Fallback local só deve ser usado com `--allow-local-token`, nunca em `.env` do projeto.

Diagnóstico:

```bash
tide taiga doctor
tide taiga show
tide taiga whoami
```

Remoção local:

```bash
tide taiga logout
```

## Quando usar

Use quando o supervisor disser algo equivalente a:

- "pode levar para o Taiga";
- "registre isso no Taiga";
- "quero realizar a atividade #231 do Taiga";
- "vincule esta Wave à atividade #231";
- "sincronize com o Taiga".

Também use quando a Wave já tiver vínculo Taiga ativo.

Não use Taiga em fluxo normal de código sem sinalização explícita.

## Regra obrigatória antes de escrever

Antes de qualquer alteração real no Taiga, mostre exatamente o que será alterado e aguarde autorização ou ajuste do supervisor.

Fluxo obrigatório:

1. rode o comando com `--dry-run`;
2. mostre o plano ao supervisor;
3. aguarde aprovação explícita ou ajuste;
4. só depois rode o mesmo comando com `--yes` e sem `--dry-run`.

Não pule o preview mesmo quando a Wave já estiver vinculada ao Taiga.

## Comandos operacionais

Read-only:

```bash
tide taiga whoami
tide taiga projects
tide taiga statuses --kind task
tide taiga members
tide taiga list --kind task
tide taiga find --kind task --contains "termo"
tide taiga get --kind task --ref 231
tide taiga maturity --kind task --ref 231
```

Preview de escrita:

```bash
tide taiga create --kind task --subject "Título" --description "Descrição" --dry-run
tide taiga comment --kind task --ref 231 --text "Comentário" --dry-run
tide taiga update --kind task --ref 231 --status "Em andamento" --dry-run
tide taiga sync TIDE-0005 --dry-run
tide taiga create-from-wave TIDE-0005 --kind task --dry-run
```

Escrita no Taiga exige `--yes` e aprovação explícita do supervisor após o preview:

```bash
tide taiga create --kind task --subject "Título" --description "Descrição" --yes
tide taiga comment --kind task --ref 231 --text "Comentário" --yes
tide taiga update --kind task --ref 231 --status "Em andamento" --yes
tide taiga sync TIDE-0005 --yes
tide taiga create-from-wave TIDE-0005 --kind task --yes
```

Para texto longo, use stdin diretamente no comando Tide:

```bash
tide taiga create --kind task --subject "Título" --description-stdin --dry-run <<'EOF'
Descrição longa.
EOF

tide taiga comment --kind task --ref 231 --text-stdin --dry-run <<'EOF'
Comentário longo.
EOF

tide taiga update --kind task --ref 231 --description-stdin --dry-run <<'EOF'
Descrição atualizada.
EOF
```

Depois da aprovação, repita com `--yes`.

Vínculo local de Wave, sem escrever no Taiga:

```bash
tide taiga link TIDE-0005 --kind task --ref 231
```

## Ciclo suportado

### Planejamento maduro para Taiga

Quando o planejamento local estiver maduro e o supervisor pedir para levar ao Taiga:

- transforme o plano em item organizacional;
- inclua objetivo, escopo, fora de escopo, critérios de aceite, validação esperada e riscos;
- mostre o preview com `--dry-run`;
- após aprovação, use `tide taiga create-from-wave <id> --yes` ou `tide taiga create ... --yes`;
- após criar, registre ref visível e vincule à Wave quando possível.

### Atividade existente no Taiga

Quando o supervisor pedir para trabalhar em uma ref, como `#231`:

- use `tide taiga get --kind task --ref 231` para ler;
- use `tide taiga maturity --kind task --ref 231` para avaliar maturidade;
- proponha ajuste se objetivo/escopo/critérios/validação estiverem vagos;
- mostre preview antes de editar descrição/status/assignee/sprint;
- use `tide taiga link <wave> --ref 231` para vincular a Wave.

### Trabalho local para Taiga

Quando o trabalho já foi feito localmente:

- use Wave, validações, code-report e commit se existirem;
- mostre preview com `tide taiga create-from-wave <id> --dry-run` ou `tide taiga sync <id> --dry-run`;
- só execute com `--yes` após aprovação explícita;
- não invente evidência ausente.

## Escrita e confirmação

Escritas sensíveis exigem confirmação explícita:

- criar item;
- editar descrição;
- mover status;
- trocar assignee;
- trocar sprint;
- atualizar campos organizacionais.

Comentar progresso/fechamento pode ser automático somente depois de preview aprovado quando:

- a Wave já está vinculada ao Taiga;
- `taiga.enabled=true` ou equivalente;
- `auto_sync=true`;
- a operação não altera status/assignee/sprint.

## Eventos naturais da Wave

Depois que Taiga estiver ativo para uma Wave, o supervisor não deve precisar pedir checkpoints manuais.

O Tide pode propor sincronização em eventos naturais:

- criação/planejamento;
- park;
- finish/validated;
- approve/committed;
- reject.

Mesmo nesses eventos, a escrita real no Taiga passa por preview e autorização.

Falha no Taiga não desfaz commit ou estado local. Reporte a falha e recomende retry.

## Metadados locais da Wave

O vínculo recomendado é local, dentro de `.opencode/waves/<id>/wave.json`:

```json
{
  "taiga": {
    "enabled": true,
    "ref": 231,
    "kind": "task",
    "project_id": 43,
    "auto_sync": true,
    "created_by_tide": false,
    "last_sync": null
  }
}
```

Esses metadados não são credenciais e não devem ir para o Git.

## Segurança

- Nunca exponha token.
- Nunca escreva segredo em comentários do Taiga.
- Use ref visível (`#231`) quando existir, não ID interno.
- Confirme membros/status antes de atribuir ou mover.
- Não acople Taiga a órgão, empresa ou projeto específico.
- Não implemente comportamento específico de ETIPI no core do Tide.

## Formato de comentário recomendado

```txt
Tide — <TIDE-ID>

Status: <running|parked|validated|committed|rejected>
Resumo:
- ...

Validação:
- ...

Riscos/restos:
- ...

Commit:
- <hash, quando existir>
```

Use linguagem organizacional; evite excesso de detalhe técnico.
