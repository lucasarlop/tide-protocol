# Tide Protocol

Tide Protocol é um runtime de desenvolvimento assistido por IA para OpenCode, baseado em **Waves identificáveis**, **fronteiras explícitas**, **código durável**, **validação proporcional ao risco** e **supervisão humana**.

O software é o mar. As Waves são movimentos controlados sobre ele: podem investigar, implementar, validar, operar, revisar, estacionar, ser aprovadas, rejeitadas ou agrupadas em commits.

## Status

Versão atual: **0.2.0**.

Esta versão entrega o runtime local de Waves com snapshots por árvore Git, approve/reject seguro e instalação global para OpenCode. MCP Tide e integração profunda com `code-review-graph` ficam para próximas Waves.

## Ideia central

O Tide não é Spec-First nem Pipeline-First. Ele é **Boundary-First**:

1. o agente entende a intenção;
2. define a menor Wave segura;
3. declara fronteiras e validação;
4. age com liberdade dentro da fronteira;
5. para se precisar cruzar a fronteira;
6. entrega evidência ao supervisor;
7. o supervisor decide se aprova, rejeita, acumula ou continua.

## Vocabulário

- **Mar**: o software atual. A fonte da verdade é o código presente, não histórico de decisões.
- **Wave**: unidade identificável de movimento sobre o software. Exemplo: `TIDE-0001`.
- **Fronteira**: o que a Wave pode tocar, executar ou decidir.
- **Evidência**: prova proporcional ao risco: teste, comando, diff, log, checklist ou validação manual.
- **Checkpoint**: ponto em que o supervisor decide o próximo movimento.
- **Código durável**: código que falha bem, orienta bem, opera bem e deixa claro onde ajustar.

## Instalação global

```bash
git clone https://github.com/lucasarlop/tide-protocol.git /tmp/tide-protocol
cd /tmp/tide-protocol
bash install.sh
```

O instalador copia agentes, comandos, skills e regras para a configuração global do OpenCode em `~/.config/opencode/` e instala o CLI em `~/.local/bin/tide`.

Opções:

```bash
bash install.sh --dry-run
bash install.sh --force
bash install.sh --config-dir /path/to/opencode-config
bash install.sh --bin-dir /path/to/bin
```

Depois:

```bash
cd qualquer-projeto
opencode
```

## Estado local de Waves

Em cada projeto:

```bash
tide init
```

Isso cria estado operacional local em:

```txt
.opencode/waves/
  registry.json
  TIDE-0001/
    wave.md
    wave.json
    wave.diff
    files.json
    validations.json
```

Esse diretório é ignorado localmente via `.git/info/exclude`, não via `.gitignore`. Assim o Tide não polui o repositório do projeto.

## Ciclo de Wave

```txt
running     → Wave existe e está em andamento
parked      → Wave parou, mas ainda não foi aprovada nem rejeitada
validated   → Wave tem evidência, mas ainda aguarda decisão do supervisor
committed   → Wave foi aprovada em commit
rejected    → Wave foi revertida
failed      → Wave falhou ou ficou insegura/inconclusiva
```

Importante:

```txt
parked/validated ≠ committed
```

Você pode seguir em várias Waves antes de decidir o que aprovar ou rejeitar.

## Comandos slash

```txt
/waves
```

Lista Waves abertas, estacionadas, rejeitadas e commitadas.

```txt
/wave TIDE-0001
```

Mostra detalhes de uma Wave.

```txt
/approve TIDE-0001
```

Commita a Wave com mensagem incluindo o ID.

```txt
/approve TIDE-0001 TIDE-0002
```

Commita múltiplas Waves juntas, na ordem informada.

```txt
/reject TIDE-0001
```

Reverte a Wave, se o patch reverso aplicar limpo.

```txt
/btw <pergunta>
/teach <tema>
```

Bypasses: não alteram Waves nem código.

## CLI

```bash
tide init
```

Inicializa `.opencode/waves/` no projeto atual.

```bash
tide wave create --title "Corrigir validação de DATABASE_URL" --type code --risk medium --max-files 3
```

Cria a próxima Wave e captura uma baseline da árvore atual do worktree.

```bash
tide wave snapshot TIDE-0001 --status parked --note "Implementação pronta para validação manual"
```

Captura o diff da Wave desde a baseline até o worktree atual.

```bash
tide wave park TIDE-0001 --validation "pytest tests/config -x --tb=short"
```

Atalho para snapshot estacionado.

```bash
tide wave list
```

Lista Waves.

```bash
tide wave show TIDE-0001
```

Mostra `wave.md`.

```bash
tide wave status TIDE-0001
```

Mostra status curto.

```bash
tide wave approve TIDE-0001
```

Cria commit a partir do patch salvo da Wave.

```bash
tide wave approve TIDE-0001 TIDE-0002
```

Cria commit agrupando as Waves informadas.

```bash
tide wave reject TIDE-0001
```

Aplica o reverse patch da Wave.

Aliases compatíveis:

```bash
tide waves
tide wave TIDE-0001
tide approve TIDE-0001
tide reject TIDE-0001
tide snapshot TIDE-0001
tide park TIDE-0001
```

## Isolamento de Waves

Cada Wave captura uma baseline da árvore do worktree no momento da criação. O snapshot compara essa baseline com o worktree atual.

Isso permite:

- estacionar Waves sem commit;
- criar novas Waves sobre mudanças ainda não commitadas;
- aprovar uma Wave isolada quando o patch aplicar limpo;
- aprovar múltiplas Waves juntas;
- rejeitar uma Wave quando o reverse patch aplicar limpo.

Se uma Wave depender de outra no mesmo hunk/contexto, o approve/reject isolado deve falhar e pedir ação agrupada ou manual. O Tide prefere parar a destruir mudança silenciosamente.

## Agentes

Agente principal:

- `tide` — orquestrador; decide intenção, risco, fronteira, Wave e subagentes.

Subagentes:

- `tide-guide` — dúvidas sobre o projeto, read-only.
- `tide-runner` — implementa mudanças dentro da fronteira.
- `tide-operator` — comandos, scripts, banco, SSH e rotinas operacionais.
- `tide-verifier` — validações/testes com runtime policy.
- `tide-steward` — estado de Waves, approve/reject e commits.
- `tide-reviewer-durability` — código durável.
- `tide-reviewer-simplicity` — simplicidade e overengineering.
- `tide-reviewer-tests` — qualidade das verificações.
- `tide-reviewer-security` — auth, permissões, tokens, secrets, SSH e produção.
- `tide-reviewer-data` — banco, migrations, queries, integridade e reprocessamentos.
- `tide-reviewer-infra` — Docker, CI/CD, deploy, env vars, filas, workers, cache e runtime.

## Princípios

O Tide reaproveita os princípios do `opencode-pack`:

- comunicação direta;
- simplicidade primeiro;
- não inventar escopo;
- menos código;
- decisões explícitas;
- honestidade técnica;
- evitar overengineering.

E acrescenta:

- código deve durar;
- comandos longos precisam de timeout/critério de parada;
- o supervisor decide approve/reject/commit;
- commit nunca é automático.
