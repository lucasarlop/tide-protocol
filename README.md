# Tide Protocol

Tide Protocol é um runtime de desenvolvimento assistido por IA para OpenCode, baseado em **Waves identificáveis**, **fronteiras explícitas**, **código durável**, **validação proporcional ao risco**, **hardgates**, **SMART** e **supervisão humana**.

O software é o mar. As Waves são movimentos controlados sobre ele: podem investigar, implementar, validar, operar, revisar, estacionar, ser aprovadas, rejeitadas ou agrupadas em commits.

## Status

Versão atual: **0.5.0**.

Esta versão entrega o MVP operacional do Tide: CLI Python com Waves locais, approve/reject supervisionado, catálogo de comandos de projeto, runtime com timeout, agentes/comandos/skills globais para OpenCode, CI, instalação isolada, launcher `tide opencode`, `tide doctor`, guias de instalação/operação, Código Vivo, MCP seguro de contexto, hardgates, SMART, commit safety e política dinâmica de modelo/effort.

## Ideia central

O Tide não é Spec-First nem Pipeline-First. Ele é **Boundary-First**:

1. o agente entende a intenção;
2. define a menor Wave segura;
3. declara fronteiras, SMART, hardgates e validação;
4. age com liberdade dentro da fronteira;
5. para se precisar cruzar a fronteira;
6. entrega evidência ao supervisor;
7. o supervisor decide se aprova, rejeita, acumula ou continua.

## Vocabulário

- **Mar**: o software atual. A fonte da verdade é o código presente, não histórico de decisões.
- **Wave**: unidade identificável de movimento sobre o software. Exemplo: `TIDE-0001`.
- **Fronteira**: o que a Wave pode tocar, executar ou decidir.
- **Hardgate**: condição que obriga o agente a parar e pedir checkpoint antes de agir.
- **SMART**: critério mínimo para uma Wave ser específica, mensurável, alcançável, relevante e time-boxed.
- **Evidência**: prova proporcional ao risco: teste, comando, diff, log, checklist ou validação manual.
- **Checkpoint**: ponto em que o supervisor decide o próximo movimento.
- **Código durável**: código que falha bem, orienta bem, opera bem e deixa claro onde ajustar.

## Instalação recomendada

O padrão seguro é instalação isolada, para não afetar projetos que já usam `opencode-pack` ou outra configuração global do OpenCode.

```bash
git clone https://github.com/lucasarlop/tide-protocol.git /tmp/tide-protocol
cd /tmp/tide-protocol
bash install.sh --force
```

Isso instala:

```txt
~/.config/opencode-tide/   agentes, comandos, skills, regras e MCP
~/.local/bin/tide          launcher Tide
~/.local/bin/tide-cli      CLI operacional real
~/.local/bin/tide.config   config usada pelo launcher
```

Abra um projeto com:

```bash
cd qualquer-projeto
tide opencode
```

`tide opencode` roda `tide init` por padrão e abre o OpenCode com a config isolada do Tide.

Diagnóstico:

```bash
tide doctor
```

Instalação global exige intenção explícita:

```bash
bash install.sh --global --force
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

Depois de `validated`, o Tide evita rebaixar a Wave para `parked` sem confirmação explícita.

## CLI essencial

Criar uma Wave:

```bash
tide wave create --title "Corrigir validação de DATABASE_URL" --type code --risk medium --max-files 3
```

Estacionar a Wave com snapshot do diff atual:

```bash
tide wave park TIDE-0001 --note "Implementação pronta para validação"
```

Finalizar uma Wave validada em uma operação:

```bash
tide wave finish TIDE-0001 \
  --summary "teste escopado passou" \
  --command "tide run --timeout-sec 120 --silence-sec 60 -- python3 -m unittest tests.test_config" \
  --result passed
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

## Commit safety

`approve` é restritivo por padrão. Ele exige:

- índice Git limpo antes do approve;
- Wave `validated`;
- arquivos registrados;
- snapshot salvo;
- diff atual coerente com o snapshot salvo;
- ausência de overlap com Waves ativas, salvo decisão explícita;
- commit sem push.

Flags de bypass existem somente para hardgates supervisionados:

```bash
tide approve TIDE-0001 --allow-unvalidated
tide approve TIDE-0001 --allow-snapshot-drift
tide approve TIDE-0001 --allow-overlap
```

## Catálogo de comandos do projeto

O Tide descobre comandos de:

- `package.json`;
- `Makefile`;
- scripts em `bin/`, `scripts/` e `tools/`;
- catálogos opcionais em `.tide/commands.json`, `.tide.commands.json`, `tide.commands.json` ou `.opencode/tide/commands.json`.

Listar comandos:

```bash
tide project commands
tide project commands --json
```

Executar comando catalogado:

```bash
tide project run regenerate_book --arg book_id=123 --dry-run
tide project run regenerate_book --arg book_id=123 --yes
```

Comandos com `safety` sensível ou `requires_ok: true` exigem `--yes`, que representa OK explícito do supervisor.

Execução direta com timeout:

```bash
tide run --timeout-sec 120 --silence-sec 60 -- pytest tests/config -x
```

Códigos especiais:

```txt
124 = timeout hard
125 = timeout por silêncio
```

## Hardgates e SMART

Hardgates comuns:

- produção;
- deploy;
- CI/CD;
- SSH;
- banco de dados;
- migrations;
- reprocessamento;
- scripts destrutivos;
- auth/permissões/tokens/secrets;
- API pública;
- nova dependência;
- alteração ampla em muitos arquivos;
- validação inconclusiva.

Wave relevante deve ser SMART antes de executar: específica, mensurável, alcançável, relevante e time-boxed.

## Modelo e modo fast

O modo padrão é **balanced-quality dinâmico**. O Tide escolhe esforço por risco:

```txt
medium → tarefa clara, pequena e baixo risco
high   → código relevante, lógica de domínio, durabilidade ou testes não triviais
xhigh  → segurança, dados, infra crítica, produção, permissões ou código de alto impacto
```

O supervisor pode pedir `modo fast` quando quiser priorizar velocidade. Fast mode reduz investigação ampla e reviewers desnecessários, mas preserva hardgates.

## Tide MCP

O Tide MCP começa como camada segura de contexto e planejamento. Ele não substitui os agentes do OpenCode e não transforma o MCP em executor cego de comandos.

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

## Agentes

Agente principal:

- `tide` — orquestrador; decide intenção, risco, fronteira, Wave, hardgates, effort e subagentes.

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
- hardgates interrompem execução;
- o supervisor decide approve/reject/commit;
- commit nunca é automático.
