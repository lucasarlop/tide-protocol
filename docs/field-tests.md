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

## Próximo field test sugerido — fluxo médio/complexo

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
