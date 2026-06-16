# Tide Protocol

Tide Protocol é um runtime de desenvolvimento assistido por IA para OpenCode, baseado em **Waves identificáveis**, **fronteiras explícitas**, **código durável**, **validação proporcional ao risco** e **supervisão humana**.

O software é o mar. As Waves são movimentos controlados sobre ele: podem investigar, implementar, validar, operar, revisar, estacionar, ser aprovadas, rejeitadas ou agrupadas em commits.

## Status

Versão atual: **0.5.0**.

Esta versão entrega o MVP operacional do Tide: CLI Python com Waves locais, approve/reject supervisionado, catálogo de comandos de projeto, runtime com timeout, agentes/comandos/skills globais para OpenCode, CI, guias de instalação/operação, Código Vivo e MCP seguro de contexto.

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
tide init
opencode
```

## Estado local de Waves

`tide init` cria estado operacional local em:

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

## CLI

Criar uma Wave:

```bash
tide wave create --title "Corrigir validação de DATABASE_URL" --type code --risk medium --max-files 3
```

Estacionar a Wave com snapshot do diff atual:

```bash
tide wave park TIDE-0001 --note "Implementação pronta para validação manual"
```

Registrar evidência:

```bash
tide wave validate TIDE-0001 --summary "pytest tests/config -x passou" --command "pytest tests/config -x" --result "passed" --status validated
```

Inspecionar:

```bash
tide wave list
tide wave show TIDE-0001
tide wave status TIDE-0001
tide wave diff TIDE-0001 --stat
tide wave files TIDE-0001
```

Aprovar ou rejeitar:

```bash
tide approve TIDE-0001
tide approve TIDE-0001 TIDE-0002
tide reject TIDE-0001
```

Aliases compatíveis:

```bash
tide waves
tide create-wave "Título curto"
tide snapshot TIDE-0001
tide park TIDE-0001
tide wave approve TIDE-0001
tide wave reject TIDE-0001
```

## Catálogo de comandos do projeto

O Tide descobre comandos de:

- `package.json`;
- `Makefile`;
- scripts em `bin/`, `scripts/` e `tools/`;
- catálogos opcionais em `.tide/commands.json`, `.tide.commands.json` ou `tide.commands.json`.

Listar comandos:

```bash
tide project commands
tide project commands --json
```

Explicar um comando:

```bash
tide project command regenerate_book
```

Executar comando catalogado:

```bash
tide project run regenerate_book --arg book_id=123 --dry-run
tide project run regenerate_book --arg book_id=123 --yes
```

Comandos com `safety` sensível ou `requires_ok: true` exigem `--yes`, que representa OK explícito do supervisor. Timeout retorna resultado inconclusivo, não sucesso.

Também há execução direta com timeout:

```bash
tide run --timeout-sec 120 --silence-sec 60 -- pytest tests/config -x
```

Códigos especiais:

```txt
124 = timeout hard
125 = timeout por silêncio
```

## Tide MCP

O Tide MCP começa como camada segura de contexto e planejamento. Ele não substitui os agentes do OpenCode e não transforma o MCP em executor cego de comandos.

Arquivo atual:

```txt
mcp/tide_mcp.py
```

Contrato inicial:

```txt
tide_project_profile
tide_wave_list
tide_wave_show
tide_commands_list
tide_command_plan
tide_context_status
```

A execução operacional permanece no CLI `tide`, nos comandos slash e nos agentes, respeitando supervisor OK, `safety`, `requires_ok`, timeout e validação.

## Código Vivo

`code-review-graph` é integração recomendada, não dependência obrigatória. O Tide usa contexto indexado quando disponível, mas a fonte da verdade continua sendo:

```txt
código atual + git status + diff + validações reais
```

Se não houver índice, o agente deve usar leitura direta do código atual.

## Comandos slash

```txt
/waves
/wave TIDE-0001
/approve TIDE-0001
/approve TIDE-0001 TIDE-0002
/reject TIDE-0001
/park TIDE-0001
/project-commands
/project-run <comando catalogado>
/btw <pergunta>
/teach <tema>
```

`/approve` e `/reject` só acontecem quando o supervisor pede explicitamente. Commit nunca é automático.

## Isolamento de Waves

Cada Wave salva arquivos, patch e metadados locais. O Tide prefere parar a destruir mudança silenciosamente.

Regras atuais:

- approve de uma Wave faz commit dos arquivos registrados no snapshot;
- approve de múltiplas Waves agrupa os arquivos registrados;
- se houver outra Wave ativa tocando o mesmo arquivo, o approve isolado bloqueia, salvo `--allow-overlap`;
- reject usa reverse patch e falha se não aplicar limpo.

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
