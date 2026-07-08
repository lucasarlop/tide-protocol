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

## Ciclo suportado

### Planejamento maduro para Taiga

Quando o planejamento local estiver maduro e o supervisor pedir para levar ao Taiga:

- transforme o plano em item organizacional;
- inclua objetivo, escopo, fora de escopo, critérios de aceite, validação esperada e riscos;
- peça confirmação antes de criar item real;
- após criar, registre ref visível e vincule à Wave quando possível.

### Atividade existente no Taiga

Quando o supervisor pedir para trabalhar em uma ref, como `#231`:

- buscar a atividade quando a API real estiver disponível;
- avaliar maturidade antes de implementar;
- propor ajuste se objetivo/escopo/critérios/validação estiverem vagos;
- pedir confirmação antes de editar descrição/status/assignee/sprint;
- criar ou orientar criação de Wave vinculada.

### Trabalho local para Taiga

Quando o trabalho já foi feito localmente:

- usar Wave, validações, code-report e commit se existirem;
- criar ou atualizar item com histórico consolidado;
- não inventar evidência ausente.

## Escrita e confirmação

Escritas sensíveis exigem confirmação explícita:

- criar item;
- editar descrição;
- mover status;
- trocar assignee;
- trocar sprint;
- atualizar campos organizacionais.

Comentar progresso/fechamento pode ser automático somente quando:

- a Wave já está vinculada ao Taiga;
- `taiga.enabled=true` ou equivalente;
- `auto_sync=true`;
- a operação não altera status/assignee/sprint.

## Eventos naturais da Wave

Depois que Taiga estiver ativo para uma Wave, o supervisor não deve precisar pedir checkpoints manuais.

O Tide pode sincronizar em eventos naturais:

- criação/planejamento;
- park;
- finish/validated;
- approve/committed;
- reject.

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
