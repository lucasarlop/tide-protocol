# Roadmap para Tide Protocol 1.0

O Tide 0.5.0 é o MVP operacional. O 1.0 deve ser marcado somente quando o protocolo estiver testado em projetos reais e com política de modelos consolidada.

## Pendências críticas antes do 1.0

### TIDE-0011 — Model Policy e qualidade/custo

Status: iniciado.

Entregas:
- documentar política de modelos;
- fixar modelos/variants nos agentes quando os IDs reais forem confirmados;
- limitar steps por agente;
- criar perfis `balanced-quality`, `quality` e `economy`;
- garantir que `tide-steward` e `tide-verifier` não herdem sempre modelo caro;
- garantir que `tide-runner` possa usar high/xhigh quando qualidade de código importar.

### TIDE-0012 — Delegação correta de código

Problema observado no demo:
- agente principal editou arquivo via shell/script;
- ideal é delegar implementação ao `tide-runner`.

Entregas:
- reforçar prompt do `tide` para não editar código;
- reforçar `tide-runner` como responsável por mudanças;
- manter `tide` como orquestrador;
- garantir que baixo risco use fluxo enxuto.

### TIDE-0013 — Lifecycle validate/park

Problema observado no demo:
- Wave foi validada e depois estacionada, podendo rebaixar status para `parked`.

Entregas:
- depois de `validated`, não chamar `park` de novo;
- preferir `snapshot` com status `validated` quando houver validação;
- checkpoint final deve consultar o status real da Wave antes de responder.

### TIDE-0014 — Runtime policy obrigatória

Problema observado no demo:
- teste foi rodado diretamente com `python3 -m unittest` em vez de `tide run`.

Entregas:
- toda validação executável deve usar `tide run` ou `tide project run`, salvo justificativa explícita;
- catálogo do projeto deve ser preferido quando existir;
- `python3` deve ser preferido a `python` quando não houver comando catalogado.

### TIDE-0015 — Instalação isolada como caminho padrão de teste

Problema:
- instalação global pode interferir com `opencode-pack` em projetos existentes.

Entregas:
- manter instalação isolada como recomendação padrão de teste;
- documentar `OPENCODE_CONFIG_DIR=$HOME/.config/opencode-tide opencode`;
- evitar sobrescrever comandos globais do usuário sem confirmação.

### TIDE-0016 — MCP e OpenCode config

Entregas:
- fornecer exemplo real de config OpenCode com MCP Tide;
- garantir caminho absoluto para `tide_mcp.py`;
- manter MCP context-only por padrão;
- deixar execução real no CLI e no supervisor.

### TIDE-0017 — Testes de campo

Antes do 1.0, validar em pelo menos:

1. projeto demo;
2. um projeto Python real;
3. um projeto Node/JS real;
4. um projeto com comandos operacionais catalogados;
5. um projeto que já usa `opencode-pack`, usando instalação isolada.

## Critérios de 1.0

Marcar 1.0 somente quando:

- CI passar;
- instalação isolada funcionar sem afetar `opencode-pack`;
- agente criar Waves sozinho a partir de pedido natural;
- mudança de código for delegada ao runner;
- validação usar `tide run` ou `tide project run`;
- status final da Wave for coerente;
- approve/reject continuar seguro;
- política de modelos estiver aplicada aos agentes;
- documentação estiver atualizada;
- pelo menos dois testes reais em projetos forem bem-sucedidos.

## Filosofia da versão 1.0

O 1.0 não precisa ter tudo que o Tide um dia pode ser. Ele precisa ser confiável para uso diário:

```txt
pedido natural → Wave → execução por subagente certo → validação com timeout → checkpoint → approve/reject seguro
```
