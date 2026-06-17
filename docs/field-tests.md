# Field Tests Tide

Field test é teste de campo do protocolo em uso real, não apenas teste unitário do CLI.

Ele valida se o fluxo humano + OpenCode + agentes + CLI funciona na prática:

```txt
pedido natural → Wave → runner/verifier/reviewer conforme risco → finish → checkpoint → approve/reject
```

## TIDE-0027 — Demo env validation

Status: aprovado com ajustes aplicados depois do teste.

Resumo:

- Wave criada automaticamente: `TIDE-0002`.
- Implementação delegada ao `tide-runner`.
- Validação delegada ao `tide-verifier`.
- Teste escopado passou com `tide run`.
- Approve explícito criou commit.
- Wave terminou `committed`.
- Working tree terminou limpo.

Problemas observados:

1. `tide-verifier` investigou antes de executar o comando e estourou steps.
2. Validação foi registrada com `tide wave validate --status validated` em vez de `tide wave finish`.
3. Skill `tide-wave` ainda ensinava snapshot antigo.
4. `tide-steward` gastou passos demais no approve e tentou delegar/checar além do necessário.
5. `tide` usou subagente genérico `explore` em uma tarefa simples.
6. O primeiro prompt ao verifier deu comando candidato em vez de comando exato com `tide run`.

Ajustes aplicados:

- `tide-verifier` deve executar comando exato seguro primeiro.
- `tide-verifier` deve preferir `tide wave finish` quando validação passar.
- `tide-wave` exige `finish` antes de oferecer `/approve`.
- `tide-steward`, `/approve`, `/reject` e `tide-commit` foram otimizados para confiar no CLI seguro.
- `tide` foi orientado a não usar subagente genérico `explore` e a evitar exploração prévia em baixo risco.
- `tide-runtime-policy` foi reforçada com `tide run`, `python3` e comando exato para verifier.

## TIDE-0029 — Demo config validation composta

Status: aprovado com ajuste crítico identificado depois do teste.

Resumo:

- Wave criada automaticamente: `TIDE-0003`.
- Implementação delegada ao `tide-runner`.
- Runner implementou `DemoConfig` e `load_demo_config()`.
- Verifier executou validação escopada com `tide run`.
- Verifier usou `tide wave finish` corretamente.
- Steward executou `/approve` de forma curta e direta.
- Commit criado: `f8b11e0`.
- Working tree reportado como limpo após approve.

O que melhorou em relação ao TIDE-0027:

- `tide-wave` carregada já estava atualizada.
- `tide wave finish` foi usado.
- `tide-steward` não estourou steps.
- `/approve` foi direto e resumiu output do CLI.

Problema crítico observado:

- Havia arquivo modificado fora da fronteira (`session-ses_129f.md`) no working tree.
- O verifier observou esse arquivo, mas ainda assim executou `tide wave finish`.
- Como o CLI atual captura o working tree sujo da Wave, isso pode misturar mudanças fora da fronteira no snapshot/commit.

Ajustes aplicados:

- `tide-verifier` agora deve bloquear `finish` quando houver arquivo modificado fora da fronteira.
- `tide-wave` agora trata arquivo sujo fora da fronteira como hardgate antes de `finish` e `/approve`.

Próxima otimização técnica recomendada:

- endurecer o CLI para permitir snapshot/finish por arquivos explícitos ou por fronteira (`--file`/`--allow`) e evitar que arquivo fora da Wave entre no snapshot por acidente.

## TIDE-0030 — Boundary dirty-tree test

Status: aprovado com ajuste de ergonomia aplicado depois do teste.

Resumo:

- Wave criada automaticamente: `TIDE-0004`.
- Fronteira rígida: `src/tide_demo/config.py` e `tests/test_config.py`.
- Runner alterou apenas arquivos permitidos.
- Verifier executou teste escopado.
- Verifier detectou arquivos fora da fronteira: `notes.tmp` e `session-ses_129d.md`.
- Verifier não executou `tide wave finish`.
- Checkpoint não ofereceu `/approve`.
- Wave permaneceu `running`.

Resultado esperado confirmado:

- arquivo sujo fora da fronteira bloqueia `finish`;
- supervisor precisa decidir limpar, separar, estacionar ou incluir explicitamente.

Problema de ergonomia observado:

- O runner executou teste direto e pediu permissão do usuário para comando seguro/escopado.
- O runner também atingiu limite de steps.

Ajustes aplicados:

- `tide-runner` agora deve deixar validação para o `tide-verifier` quando o fluxo normal disser que verifier validará depois.
- `tide-runner` recebeu allowlist para comandos seguros e escopados como `tide run *` e `python3 -m unittest tests*`.
- `tide` agora deve dizer explicitamente ao runner: não rode testes; o verifier validará depois.

Próxima otimização técnica recomendada:

- mover a regra de fronteira para o CLI: `tide wave finish --file ...` ou finish por arquivos permitidos, reduzindo dependência de prompt.

## Próximo field test sugerido — permission/runner ergonomics

Objetivo: confirmar que o runner não pede permissão desnecessária nem roda teste que o verifier vai repetir.

Preparação:

- limpe arquivos fora da fronteira do projeto demo;
- reinstale Tide após CI verde.

Pedido sugerido:

```txt
@tide ajuste uma mensagem pequena em `src/tide_demo/config.py`, mantendo a fronteira em `src/tide_demo/config.py` e `tests/test_config.py`. Não rode testes no runner; deixe o verifier validar com teste escopado.
```

Critério de aprovação:

- runner não executa teste;
- nenhuma permissão para `python3 -m unittest` aparece no runner;
- verifier executa teste uma vez;
- verifier usa `tide wave finish` se a fronteira estiver limpa;
- checkpoint oferece `/approve` apenas após `validated`.

## Field test médio/complexo sugerido depois

Objetivo: testar fluxo mais completo sem entrar em produção, banco real ou deploy.

Projeto alvo ideal:

- projeto demo ou projeto Python real pequeno;
- com pelo menos 3 arquivos tocáveis;
- com comando catalogado em `tide.commands.json`;
- sem credenciais reais;
- sem dependência externa cara.

Pedido sugerido:

```txt
@tide implemente uma validação de configuração composta para o projeto: além de validar env obrigatória, crie uma função que carregue `DEMO_TOKEN` e `DEMO_TIMEOUT_SECONDS`, valide que o token não está vazio e que o timeout é inteiro positivo. Mantenha simples, sem novas dependências, preserve mensagens acionáveis, atualize testes escopados e use o catálogo de comandos quando fizer sentido.
```

O que esse teste avalia:

- Wave média com mais de um comportamento;
- fronteira em 2 a 3 arquivos;
- decisão sobre testes novos;
- possível reviewer de durabilidade/testes;
- verifier usando comando exato com `tide run` ou catálogo;
- uso correto de `tide wave finish`;
- checkpoint com SMART e riscos;
- `/approve` curto via steward.

Critérios de aprovação:

- `tide doctor` passa antes;
- `tide opencode` é usado;
- Wave criada sem comando manual do supervisor;
- sem subagente genérico `explore` em baixo/médio risco;
- runner implementa, primary não edita;
- verifier executa comando na primeira chamada quando o comando for claro;
- finalização usa `tide wave finish`;
- checkpoint só oferece `/approve` se a Wave estiver realmente aprovável;
- steward executa `tide approve` diretamente e não estoura steps;
- commit criado e working tree limpo.

## Como registrar resultado

Use este formato:

```txt
Field test: TIDE-00XX — nome
Projeto:
Data:
Status: aprovado | aprovado com ajuste | falhou
Wave:
Commit:
Validação:
Tempo/custo percebido:
O que funcionou:
Problemas observados:
Ajustes necessários:
Próximo teste:
```
