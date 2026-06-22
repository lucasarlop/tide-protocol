---
name: tide-wave
description: Criar, conduzir, estacionar e concluir Waves com ID, fronteira, evidência e checkpoint.
license: MIT
compatibility: opencode
---

# tide-wave

Use esta skill para qualquer tarefa relevante que deva virar uma Wave.

## Preflight antes de criar Wave

Antes de criar uma Wave em projeto real, confira o working tree:

```bash
/usr/bin/git status --short
```

Se houver arquivos modificados antes da Wave:

- não crie Wave automaticamente como se o estado fosse limpo;
- reporte a sujeira inicial;
- peça decisão do supervisor: limpar, continuar como Wave empilhada, criar Wave separada, ou restringir explicitamente a fronteira;
- só continue sem perguntar quando o supervisor já tiver dito que o estado sujo é esperado e qual fronteira deve ser considerada.

Não use `rtk git status` como fonte primária de preflight. Se um wrapper retornar apenas `ok`, trate como inconclusivo para listar arquivos e use `/usr/bin/git status --short` uma única vez.

## Conceitos de parada e escopo

Separe sempre:

- **Hardgate de protocolo**: condição sensível que exige checkpoint antes de executar, como produção, deploy, banco real, dados reais, secrets, CI/CD, dependência nova, API pública, comando desconhecido ou validação inconclusiva.
- **Restrição da Wave**: limite local da Wave atual, como “não usar Milvus real nesta Wave”, “não alterar Docker”, “tocar somente arquivos X e Y”.
- **Pré-condição do plano**: decisão necessária antes de uma Wave futura, como ambiente alvo, owner, política de coleção, piloto ou produção.

Não chame toda pendência ou restrição de `hardgate`. Em checkpoints, prefira listar os três grupos separadamente.

## Wave mínima

Toda Wave deve ter:
- ID `TIDE-000N`;
- intenção;
- fronteira;
- durabilidade esperada;
- validação planejada;
- evidência;
- checkpoint.

## Wave documental ou de decisão

Quando a Wave for de planejamento, contrato ou documentação e existir chance de gerar artefato versionado:

- crie a Wave com `--max-files 1` ou outro limite realista;
- declare a fronteira na criação com `--allow <arquivo-doc>` quando o arquivo já for conhecido;
- não use `--max-files 0` se depois pretende registrar documento no Git;
- se a Wave for apenas checkpoint conversacional, não ofereça `/approve`.

Exemplo:

```bash
tide wave create \
  --title "Milvus Wave 1: decisões e contrato semântico" \
  --type plan \
  --risk medium \
  --max-files 1 \
  --allow docs/milvus-embeddings-plan.md
```

## Artefatos locais fora da Wave

Arquivos como `session-ses_*.md`, logs exportados, relatórios temporários e dumps locais não pertencem à Wave por padrão.

Se aparecerem no working tree:

- trate como sujeira fora da fronteira;
- não inclua no snapshot sem decisão explícita;
- prefira limpar/remover se forem apenas artefatos locais descartáveis;
- não use `--allow-outside-boundary` para esconder esse problema sem checkpoint.

## Fronteira suja

O CLI agora é a camada de garantia de fronteira:

- `tide wave finish --file <path>` restringe snapshot àqueles arquivos;
- se a Wave foi criada com `--allow`, `finish` usa essa fronteira quando `--file` não for informado;
- se existir arquivo modificado fora da fronteira, `finish` bloqueia por padrão;
- override só com `--allow-outside-boundary` após checkpoint explícito.

Antes de concluir uma Wave, confira se os arquivos modificados pertencem à fronteira.

Se existir arquivo modificado fora da fronteira, como log de sessão, artefato local, relatório, arquivo temporário ou mudança pré-existente:

- não ofereça `/approve`;
- reporte o arquivo fora da fronteira;
- peça decisão do supervisor: limpar, separar em outra Wave, estacionar separado, incluir explicitamente ou usar override consciente.

## Encerramento

Quando a implementação ainda não está validada:
- salve snapshot parcial com `tide wave park <id> --file <path> --note "..."` quando a fronteira for conhecida;
- não ofereça `/approve` como próxima opção principal.

Quando a validação passar e a Wave estiver pronta para checkpoint:
- use `tide wave finish <id> --file <path> --summary "..." --command "..." --result passed` quando a fronteira for conhecida;
- isso salva snapshot, arquivos, evidência e status `validated`;
- confirme o status real com `tide wave status <id>`;
- só então ofereça `/approve <id>` ou `/reject <id>`.

Ao concluir:
- informe arquivos alterados;
- informe validações;
- liste hardgates de protocolo, restrições da Wave e pré-condições futuras quando existirem;
- liste riscos/restos;
- ofereça opções: continuar, ajustar, acumular, `/approve <id>` ou `/reject <id>`.

Não commite sem pedido explícito.
