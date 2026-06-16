# Changelog

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
