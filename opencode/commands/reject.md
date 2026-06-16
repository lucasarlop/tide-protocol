---
description: Rejeita uma Wave e desfaz suas alterações.
agent: tide-steward
---

Rejeite a Wave `$ARGUMENTS`.

Regras:
- Use `tide reject $ARGUMENTS` se o CLI estiver disponível.
- Não destrua mudanças de outras Waves silenciosamente.
- Se o reverse patch não aplicar limpo, pare e explique opções.
- Não faça commit.

Ao final, mostre o status da Wave e os arquivos revertidos, se houver.
