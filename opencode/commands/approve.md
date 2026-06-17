---
description: Aprova uma Wave e cria commit com o ID da Wave.
agent: tide-steward
---

Aprove a Wave `$ARGUMENTS`.

Regras:
- O supervisor já pediu approve explicitamente.
- Não use `task`; você já é o `tide-steward`.
- Execute diretamente: `tide approve $ARGUMENTS`.
- Não faça exploração prévia por rotina.
- Não faça push.
- Se o CLI bloquear por status, snapshot, overlap, índice staged ou drift, pare e explique a mensagem do CLI.
- Se o CLI concluir com sucesso, resuma o próprio output do CLI. Não rode checagens extras salvo se o output estiver ambíguo.

Ao final, mostre de forma curta:
- comando executado;
- commit/hash quando houver;
- Waves afetadas;
- working tree reportada pelo CLI;
- pendência real, se houver.
