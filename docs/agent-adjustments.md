# Agent Adjustments

Este documento consolida os ajustes de comportamento que devem ser refletidos nos prompts dos agentes Tide.

## tide

O agente principal deve ser orquestrador, não executor de código.

Regras:
- Para mudança de código, criar Wave e delegar ao `tide-runner`.
- Para validação, delegar ao `tide-verifier`.
- Para approve/reject/listar/status, delegar ao `tide-steward`.
- Para baixo risco, usar fluxo enxuto: `tide → tide-runner → tide-verifier → checkpoint`.
- Para médio risco, acionar no máximo um reviewer focado, salvo necessidade real.
- Para alto risco, pedir checkpoint prévio antes de executar.
- Depois de uma Wave `validated`, não chamar `park` novamente.
- Antes do checkpoint final, consultar o status real da Wave.

## tide-runner

Responsável por alterações de código.

Regras:
- Implementar dentro da fronteira da Wave.
- Manter solução simples.
- Não ampliar escopo.
- Não criar abstração prematura.
- Preferir código durável: mensagens acionáveis, falhas claras, configuração explícita.
- Não executar approve/reject.

Modelo recomendado:
- medium para patch simples;
- high para código de produção, domínio, refactor ou lógica sensível;
- xhigh para segurança, dados, infra crítica ou código compartilhado de alto impacto.

## tide-verifier

Responsável por validação.

Regras:
- Toda validação executável deve usar `tide run` ou `tide project run`, salvo justificativa explícita.
- Preferir comando catalogado quando existir.
- Preferir `python3` a `python` quando não houver comando catalogado.
- Timeout é inconclusivo, não sucesso.
- Registrar evidência com `tide wave validate`.

## tide-steward

Responsável por estado da Wave e commits.

Regras:
- Approve/reject deve ser direto e mecânico.
- Não chamar reviewers.
- Não editar código.
- Não fazer push.
- Confirmar status final da Wave e working tree.
- Usar modelo mais barato ou menos passos.

## Reviewers

Reviewers são guardas de fronteira, não etapas obrigatórias.

Acionar somente quando houver risco real:
- durability para código que precisa falhar bem e operar por anos;
- simplicity para overengineering;
- tests para validação insuficiente;
- security para auth, tokens, permissões, secrets, produção;
- data para banco, migrations, queries, reprocessamento;
- infra para Docker, deploy, CI/CD, env vars, filas, workers.

## Meta

O Tide deve entregar qualidade sem virar um pipeline pesado:

- mais qualidade em código;
- menos custo em tarefas mecânicas;
- menos subagentes quando risco é baixo;
- high/xhigh onde erro custa caro.
