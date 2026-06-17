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

## Fronteira suja

Antes de concluir uma Wave, confira se os arquivos modificados pertencem à fronteira.

Se existir arquivo modificado fora da fronteira, como log de sessão, artefato local, relatório, arquivo temporário ou mudança pré-existente:

- não use `tide wave finish`;
- não ofereça `/approve`;
- reporte o arquivo fora da fronteira;
- peça decisão do supervisor: limpar, separar em outra Wave, estacionar separado ou incluir explicitamente.

## Encerramento

Quando a implementação ainda não está validada:
- salve snapshot parcial com `tide wave park <id> --note "..."`;
- não ofereça `/approve` como próxima opção principal.

Quando a validação passar e a Wave estiver pronta para checkpoint:
- use `tide wave finish <id> --summary "..." --command "..." --result passed`;
- isso salva snapshot, arquivos, evidência e status `validated`;
- confirme o status real com `tide wave status <id>`;
- só então ofereça `/approve <id>` ou `/reject <id>`.

Ao concluir:
- informe arquivos alterados;
- informe validações;
- liste riscos/restos;
- ofereça opções: continuar, ajustar, acumular, `/approve <id>` ou `/reject <id>`.

Não commite sem pedido explícito.
