---
description: Rejeita uma Wave e desfaz suas alterações.
agent: tide-steward
---

Rejeite a Wave `$ARGUMENTS`.

Regras:
- O supervisor já pediu reject explicitamente.
- Não use `task`; você já é o `tide-steward`.
- Execute diretamente: `tide reject $ARGUMENTS`.
- Não faça exploração prévia por rotina.
- Não faça commit.
- Não faça push.
- Se o CLI bloquear porque o reverse patch não aplica limpo ou porque há estado ambíguo, pare e explique a mensagem do CLI.
- Se o CLI concluir com sucesso, resuma o próprio output do CLI. Não rode checagens extras salvo se o output estiver ambíguo.

Ao final, mostre de forma curta:
- comando executado;
- Waves rejeitadas;
- working tree reportada pelo CLI, se houver;
- pendência real, se houver.
