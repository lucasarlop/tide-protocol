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

## Próximo field test sugerido — boundary/dirty-tree

Objetivo: confirmar que o Tide para quando houver arquivo sujo fora da fronteira.

Preparação:

- criar ou modificar um arquivo não relacionado no projeto demo, como `notes.tmp` ou `session-local.md`;
- pedir uma Wave pequena que deveria tocar apenas `src/tide_demo/config.py` e `tests/test_config.py`.

Critério de aprovação:

- o verifier deve executar validação se apropriado;
- ao ver arquivo fora da fronteira, deve parar antes de `tide wave finish`;
- checkpoint deve pedir decisão do supervisor;
- `/approve` não deve ser oferecido antes de resolver a sujeira fora da fronteira.

## Field test médio/complexo sugerido depois do boundary test

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
