---
name: tide-wave
description: Criar, conduzir, estacionar e concluir Waves com ID, fronteira, evidência e checkpoint.
license: MIT
compatibility: opencode
---

# tide-wave

Use esta skill para qualquer tarefa relevante que deva virar uma Wave.

## Wave mínima
Toda Wave deve ter:
- ID `TIDE-000N`;
- intenção;
- fronteira;
- durabilidade esperada;
- validação planejada;
- evidência;
- checkpoint.

## Encerramento
Ao estacionar ou concluir:
- salve snapshot se possível: `tide snapshot <id>`;
- informe arquivos alterados;
- informe validações;
- liste riscos/restos;
- ofereça opções: continuar, ajustar, acumular, `/approve <id>` ou `/reject <id>`.

Não commite sem pedido explícito.
