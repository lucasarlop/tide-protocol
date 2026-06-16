# Changelog

## [0.5.0] — 2026-06-16

### Adicionado
- CI com validação de sintaxe do CLI, testes unitários e dry-run do instalador.
- Processo de release em `docs/release.md`.
- Política de Código Vivo em `docs/live-code.md`.
- MCP seguro funcional em `mcp/tide_mcp.py` com tools context-only.
- Testes do contrato MCP seguro.
- Instalador agora copia o módulo MCP para a configuração global do OpenCode.
- Guia de instalação global e configuração MCP em `docs/install.md`.
- Guia de catálogo de comandos do projeto em `docs/project-command-catalog.md`.
- Guia de workflow do supervisor em `docs/supervisor-workflow.md`.

### Validado
- CI passou no GitHub Actions: sintaxe do CLI, testes e dry-run do instalador.

## [0.4.0] — 2026-06-16

### Adicionado
- Runtime Python real do CLI `tide`, substituindo o bash inicial.
- `tide wave validate`, `tide wave diff`, `tide wave files` e status consultável.
- `tide project command` e `tide project run` com argumentos, safety, dry-run e `--yes` para comandos sensíveis.
- `tide run` para executar comandos diretos com timeout conservador.
- Bloqueio de approve isolado quando outra Wave ativa toca os mesmos arquivos.
- Contrato inicial seguro do Tide MCP em `mcp/tide_mcp.py`.
- Documentação do MCP seguro em `mcp/README.md`.
- Estrutura inicial de testes em `tests/`.

### Alterado
- README atualizado para refletir a sintaxe real do CLI 0.4.0.
- `tide wave approve` e `tide wave reject` agora existem como aliases dos comandos top-level.

### Observações
- O timeout por silêncio em 0.4.0 usa timeout efetivo conservador; detecção streaming real fica para o runner/MCP futuro.
- O MCP inicial é deliberadamente seguro: contexto e planejamento primeiro; execução operacional permanece no CLI `tide` sob supervisão.

## [0.3.0] — 2026-06-16

### Adicionado
- Exemplo de catálogo de comandos em `examples/tide.commands.json`.
- Comandos OpenCode `/project-commands` e `/project-run` para descoberta e execução supervisionada de comandos de projeto.
- Estrutura inicial para comandos catalogados com `safety`, `requires_ok`, argumentos, timeout e validações esperadas.

### Observações
- A execução runtime completa do catálogo dentro do CLI `tide` ainda será endurecida na próxima Wave antes de ser considerada estável.

## [0.2.0] — 2026-06-16

### Adicionado
- Runtime Python do CLI `tide` com registry local em `.opencode/waves/`.
- Snapshots por árvore Git temporária, sem tocar no índice real durante a captura.
- `wave.json` para estado de máquina e `wave.md` para leitura humana/agente.
- `tide wave park`, `tide wave status` e aliases top-level.
- Approve de múltiplas Waves em um único commit.
- Reject de uma ou mais Waves via reverse patch com checagem prévia.
- Baseline `clean`/`stacked` para indicar se já havia mudanças no worktree ao criar a Wave.
- Reviewers focados para segurança, dados e infra.
- Comando slash `/park`.

### Alterado
- `.opencode/waves/` agora é ignorado via `.git/info/exclude`, evitando poluir `.gitignore` do projeto.
- Comandos slash usam `tide wave ...` como caminho principal, mantendo aliases curtos.
- `tide-steward` foi atualizado para gerenciar commit/reject sem editar código.
- README atualizado com o ciclo real de Waves e a semântica de isolamento.

### Observações
- MCP Tide e integração profunda com `code-review-graph` seguem planejados para próximas Waves.

## [0.1.0] — 2026-06-16

### Adicionado
- Definição inicial do Tide Protocol.
- Agente primário `tide` e subagentes essenciais.
- Comandos globais `/waves`, `/wave`, `/approve`, `/reject`, `/btw` e `/teach`.
- Skills iniciais para Waves, commit, runtime policy, código durável e comandos de projeto.
- Regras centrais de fronteiras, durabilidade, runtime e supervisão.
- CLI inicial `tide` com suporte local a Waves, snapshots, approve e reject.
- Instalador global para OpenCode.
