---
name: tide-commit
description: Aprovar Waves com commits seguros, incluindo o ID da Wave e sem push automático.
license: MIT
compatibility: opencode
---

# tide-commit

Use somente quando o supervisor pedir `/approve <wave-id>` ou autorização equivalente.

## Regra principal

Use o CLI seguro:

```bash
tide approve <wave-id...>
```

O CLI é responsável por:

- exigir Wave `validated` por padrão;
- exigir índice Git limpo antes do approve;
- checar snapshot contra diff atual;
- bloquear overlap sem decisão explícita;
- stagear apenas arquivos registrados na Wave;
- criar commit com ID da Wave;
- marcar status `committed`;
- não fazer push;
- reportar working tree.

## Regras do agente

- Não faça push.
- Não edite código durante commit.
- Não use `task` para delegar approve.
- Não faça exploração prévia por rotina.
- Se o CLI bloquear, explique a mensagem do CLI e pare.
- Se o CLI concluir, resuma o output do CLI; não rode checagens extras salvo se o output estiver ambíguo.

Mensagem padrão:

```txt
chore(tide): <descrição> [TIDE-000N]

Wave: TIDE-000N
```
