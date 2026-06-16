---
description: Aprova uma Wave e cria commit com o ID da Wave.
agent: tide-steward
---

Aprove a Wave `$ARGUMENTS`.

Regras:
- O supervisor já pediu approve explicitamente.
- Use `tide approve $ARGUMENTS` se o CLI estiver disponível.
- O commit deve incluir o ID da Wave na mensagem.
- Não faça push.
- Se houver conflito ou risco de misturar mudanças de outra Wave, pare e explique.

Ao final, mostre o hash do commit e o status da Wave.
