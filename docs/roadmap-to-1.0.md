# Roadmap para Tide Protocol 1.0

O Tide 0.5.0 é o MVP operacional. O 1.0 deve ser marcado somente quando o protocolo estiver testado em projetos reais, com fluxo de supervisor confiável, hardgates no CLI e política dinâmica de modelos/effort validada em uso.

## Estado atual

Concluído desde 0.5.0:

- política de modelos/effort documentada;
- `steps` aplicado em todos os agentes Tide;
- `balanced-quality` dinâmico como modo padrão;
- `modo fast` como orientação operacional opcional;
- delegação de código reforçada para `tide-runner`;
- `tide-verifier` orientado a usar `tide run` ou `tide project run`;
- lifecycle endurecido com `tide wave finish`;
- `tide wave park` não rebaixa `validated` sem confirmação explícita;
- approve/reject endurecido no CLI;
- instalação isolada como padrão seguro;
- `tide opencode` / `tide open`;
- `tide doctor`;
- hardgates e SMART documentados e presentes no agente principal;
- README e manual do supervisor atualizados;
- field tests demo detectaram e corrigiram vários problemas de fluxo;
- mapa de responsabilidades criado em `docs/responsibility-map.md`.

## Bloqueador novo antes de avançar para testes reais

### TIDE-0033 — CLI boundary hardgate

O teste em projeto real mostrou que fronteira suja não pode depender só de prompt/verifier.

Problema atual:

- `snapshot_wave()` captura todos os arquivos sujos do working tree;
- `tide wave finish` usa `snapshot_wave()`;
- em projeto real com mudanças pré-existentes, uma Wave pequena pode capturar arquivos fora da fronteira se o agente errar.

Objetivo:

- mover hardgate de fronteira para o CLI.

Critérios:

- `tide wave finish` aceita `--file <path>` repetível;
- se `--file` não for usado, o CLI usa `wave.allowed` quando existir;
- se houver arquivos sujos fora da fronteira, `finish` bloqueia por padrão;
- snapshot/patch são gerados apenas para arquivos da Wave;
- `files.json` registra apenas arquivos da Wave;
- `wave.json` registra `boundary_checked_at`, `boundary_source` e `outside_dirty_files`;
- override explícito existe apenas com nome claro, por exemplo `--allow-outside-boundary`;
- testes cobrem: dirty file fora da fronteira, finish com `--file`, approve não stageia arquivo fora da Wave.

Enquanto esse item não estiver concluído, testes em projeto real devem ser tratados como exploratórios, não como validação para 1.0.

## Pendências críticas antes do 1.0

### TIDE-0027 — Field test demo

Status: feito com ajustes posteriores.

Validar o fluxo completo em projeto demo:

```txt
tide opencode → pedido natural → Wave → runner → verifier → finish → checkpoint → approve/reject
```

Critérios:

- Wave criada sem o supervisor chamar `tide wave create` manualmente;
- implementação delegada ao `tide-runner`;
- validação usa `tide run` ou `tide project run`;
- status final fica `validated` antes do approve;
- `tide approve` cria commit seguro;
- custo/tempo aceitável.

### TIDE-0028 — Field test Python real

Status: bloqueado por TIDE-0033.

Validar em um projeto Python real pequeno.

Critérios:

- ambiente real, não só demo;
- working tree limpo ou explicitamente classificado antes de criar Wave;
- mudança pequena com teste escopado;
- `tide doctor` antes da sessão;
- `tide opencode` como entrada;
- `finish` bloqueia arquivo fora da fronteira no CLI;
- approve sem snapshot drift;
- CI ou testes locais passando.

### TIDE-0029 — Field test Node/JS real

Status: bloqueado por TIDE-0033.

Validar em projeto Node/JS.

Critérios:

- descoberta de `package.json`;
- uso de comando catalogado ou script npm descoberto;
- validação com timeout;
- checkpoint final claro;
- hardgate de fronteira garantido pelo CLI.

### TIDE-0030 — Field test com comandos operacionais catalogados

Validar projeto com `tide.commands.json` ou `.opencode/tide/commands.json`.

Critérios:

- `tide project commands` lista comandos esperados;
- `tide project run <nome> --dry-run` funciona;
- comando sensível exige `--yes`;
- hardgate operacional é respeitado.

### TIDE-0031 — Field test isolado com projeto que usa opencode-pack

Validar que Tide não interfere na configuração global existente.

Critérios:

- `opencode` continua usando configuração normal;
- `tide opencode` usa `~/.config/opencode-tide`;
- `tide doctor` encontra a config isolada;
- nenhum arquivo do `opencode-pack` é sobrescrito.

### TIDE-0032 — Confirmar IDs reais de model/variant

A política já está documentada e `steps` já está aplicado. Falta confirmar os IDs exatos aceitos pelo OpenCode para fixar `model`/`variant` com segurança.

Critérios:

- identificar o formato real de modelo no arquivo de configuração local do OpenCode;
- testar um agente com `model` e `variant` fixos;
- se funcionar, aplicar nos agentes;
- se não funcionar, manter decisão dinâmica por briefing;
- enquanto não estiver fixado, registrar `Perfil solicitado` e `Perfil observável` em subagentes críticos.

### TIDE-0034 — Release candidate 1.0

Preparar uma versão candidata.

Critérios:

- CI verde;
- README, install, supervisor manual, responsibility map e roadmap alinhados;
- changelog fechado;
- `VERSION` atualizado;
- tag candidata criada;
- instruções de rollback documentadas.

## Critérios de 1.0

Marcar 1.0 somente quando:

- CI passar;
- instalação isolada funcionar sem afetar `opencode-pack`;
- `tide opencode` for o caminho principal de entrada;
- `tide doctor` diagnosticar instalação corretamente;
- agente criar Waves sozinho a partir de pedido natural;
- mudança de código for delegada ao runner;
- validação usar `tide run` ou `tide project run`;
- status final da Wave for coerente;
- approve/reject continuar seguro;
- hardgate de fronteira estiver no CLI, não apenas em prompt;
- hardgates e SMART aparecerem nos checkpoints relevantes;
- modo fast funcionar como orientação operacional sem burlar hardgates;
- documentação estiver atualizada;
- pelo menos dois testes reais em projetos forem bem-sucedidos após TIDE-0033.

## Filosofia da versão 1.0

O 1.0 não precisa ter tudo que o Tide um dia pode ser. Ele precisa ser confiável para uso diário:

```txt
pedido natural → Wave → execução por subagente certo → validação com timeout → checkpoint → approve/reject seguro
```

O 1.0 também deve manter a regra central:

```txt
O supervisor decide. O agente propõe, executa dentro da fronteira e evidencia.
```
