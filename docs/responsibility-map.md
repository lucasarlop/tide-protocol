# Tide Responsibility Map

Este documento separa responsabilidades entre protocolo, agentes e CLI.

A regra geral é: **prompt orienta; agente decide; CLI garante**.

Se uma regra evita perda de dados, commit misturado, snapshot errado, deploy acidental ou alteração fora da fronteira, ela deve existir como hardgate no CLI ou em comando seguro equivalente. Prompt sozinho não é garantia.

## Camadas

### 1. CLI — garantias mecânicas

O CLI deve bloquear estados perigosos mesmo se o agente errar.

Responsabilidades do CLI:

- criar Waves e registrar metadados mínimos;
- controlar status de Wave;
- salvar snapshot e patch;
- impedir approve sem Wave `validated`, salvo override explícito;
- impedir approve com índice staged;
- impedir approve com snapshot drift, salvo override explícito;
- impedir approve com overlap entre Waves, salvo override explícito;
- stagear apenas arquivos registrados na Wave;
- rejeitar Wave por reverse patch com `--check` antes de aplicar;
- reportar commit/status/working tree;
- executar comandos com timeout via `tide run`/`tide project run`.

Hardgates que devem estar no CLI, não só em prompt:

- working tree suja fora da fronteira antes de `tide wave finish`;
- snapshot capturando arquivos fora da fronteira;
- arquivo fora da fronteira registrado em `files.json` sem override explícito;
- `finish` em Wave sem arquivos permitidos claros quando houver working tree sujo pré-existente;
- approve de Wave cujo snapshot inclui arquivos fora da fronteira;
- staged changes antes de approve/reject;
- snapshot drift antes de approve;
- overlap entre Waves.

### 2. Agente principal `tide` — orquestração

O agente principal deve:

- classificar intenção e risco;
- criar ou solicitar criação de Wave;
- fazer preflight de working tree antes de criar Wave em projeto real;
- definir fronteira, budget, SMART, validação esperada e hardgates;
- delegar implementação ao `tide-runner`;
- delegar validação ao `tide-verifier`;
- acionar reviewers apenas quando há risco real;
- entregar checkpoint;
- não implementar código diretamente;
- não commitar.

O `tide` pode orientar, mas não deve ser a única camada de segurança para fronteira/commit/snapshot.

### 3. `tide-runner` — implementação

O runner deve:

- editar código dentro da fronteira;
- fazer a menor mudança segura;
- não tocar fora da Wave;
- não rodar testes quando o verifier validará depois;
- informar arquivos alterados e comando escopado recomendado;
- informar perfil solicitado/observável;
- não commitar, aprovar, rejeitar ou finalizar Wave.

### 4. `tide-verifier` — evidência

O verifier deve:

- validar sem editar código;
- preferir comando escopado;
- usar `tide run` ou `tide project run`;
- não inventar API/atributo/contrato de teste;
- verificar fronteira antes de `finish`;
- chamar `tide wave finish` apenas quando validação passou e fronteira está limpa;
- reportar resultado inconclusivo quando comando/teste estiver errado;
- informar perfil solicitado/observável.

Enquanto o CLI não tiver hardgate completo de fronteira, o verifier deve ser conservador e bloquear `finish` ao detectar arquivo fora da fronteira.

### 5. `tide-steward` — decisão supervisionada

O steward deve:

- executar approve/reject apenas quando supervisor pedir explicitamente;
- usar `tide approve`/`tide reject` diretamente;
- confiar no CLI seguro;
- não explorar por rotina;
- não rodar task para delegar approve/reject;
- não fazer push;
- reportar commit/status/working tree.

## Problema atual: fronteira ainda depende demais dos agentes

No CLI atual, `snapshot_wave()` detecta todos os arquivos sujos e monta patch de todo o working tree. Isso é útil para demo simples, mas perigoso em projeto real com mudanças pré-existentes.

Comportamento desejado:

```bash
tide wave finish TIDE-0001 \
  --file backend/app/config.py \
  --summary "..." \
  --command "..." \
  --result passed
```

Ou, quando a Wave tiver `allowed` claro:

```bash
tide wave create \
  --title "..." \
  --allow backend/app/config.py \
  --max-files 1

tide wave finish TIDE-0001 --summary "..." --command "..." --result passed
```

O CLI deve:

1. calcular arquivos sujos atuais;
2. calcular fronteira permitida (`--file` explícito ou `wave.allowed`);
3. bloquear se existir arquivo sujo fora da fronteira;
4. gerar patch apenas dos arquivos da Wave;
5. salvar `files.json` apenas com arquivos da Wave;
6. registrar `boundary_checked_at`, `boundary_source` e `outside_dirty_files`.

## Overrides explícitos

Overrides podem existir, mas devem ter nome assustador e exigir checkpoint claro:

- `--allow-outside-boundary`
- `--allow-overbudget`
- `--allow-snapshot-drift`
- `--allow-overlap`

O padrão deve ser seguro.

## Status recomendado antes de novos testes reais

Antes de avançar em projeto real, implementar no CLI:

- `tide wave finish --file <path>`;
- snapshot filtrado por arquivos;
- bloqueio de arquivos sujos fora da fronteira;
- testes unitários cobrindo dirty tree fora da Wave;
- documentação no supervisor manual.
