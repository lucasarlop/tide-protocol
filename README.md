# Tide Protocol

Tide Protocol é um runtime de desenvolvimento assistido por IA para OpenCode, baseado em **Waves identificáveis**, **fronteiras explícitas**, **código durável**, **validação proporcional ao risco** e **supervisão humana**.

O software é o mar. As Waves são movimentos controlados sobre ele: podem investigar, implementar, validar, operar, revisar, estacionar, ser aprovadas, rejeitadas ou agrupadas em commits.

## Ideia central

O Tide não é Spec-First nem Pipeline-First. Ele é **Boundary-First**:

1. o agente entende a intenção;
2. define a menor Wave segura;
3. declara fronteiras e validação;
4. age com liberdade dentro da fronteira;
5. para se precisar cruzar a fronteira;
6. entrega evidência ao supervisor;
7. o supervisor decide se aprova, rejeita, acumula ou commita.

## Vocabulário

- **Mar**: o software atual. A fonte da verdade é o código presente, não histórico de decisões.
- **Wave**: unidade identificável de movimento sobre o software. Exemplo: `TIDE-0001`.
- **Fronteira**: o que a Wave pode tocar, executar ou decidir.
- **Evidência**: prova proporcional ao risco: teste, comando, diff, log, checklist ou validação manual.
- **Checkpoint**: ponto em que o supervisor decide o próximo movimento.
- **Código durável**: código que falha bem, orienta bem, opera bem e deixa claro onde ajustar.

## Waves

Toda Wave relevante deve ter representação local em arquivo:

```txt
.opencode/waves/
  registry.json
  TIDE-0001/
    wave.md
    wave.diff
    files.json
    validations.json
```

Esse diretório é estado operacional local e deve ficar ignorado pelo Git.

Uma Wave pode ficar `parked`: concluída ou interrompida, mas ainda não aprovada nem rejeitada. Isso permite seguir para outras Waves e decidir depois se elas serão agrupadas, rejeitadas ou commitadas separadamente.

## Comandos principais

```txt
/waves
  Lista Waves abertas, estacionadas, rejeitadas e commitadas.

/wave <wave-id>
  Mostra detalhes de uma Wave.

/approve <wave-id>
  Adiciona as modificações da Wave em um commit com mensagem gerada automaticamente contendo o ID.

/reject <wave-id>
  Desfaz as alterações da Wave, sem destruir mudanças de outras Waves silenciosamente.
```

`/approve` e `/reject` são opcionais no fim de cada Wave. O supervisor pode continuar trabalhando e decidir depois.

## Instalação

```bash
git clone https://github.com/lucasarlop/tide-protocol.git /tmp/tide-protocol
cd /tmp/tide-protocol
bash install.sh
```

Por padrão, o instalador copia agentes, comandos, skills e regras para a configuração global do OpenCode em `~/.config/opencode/`, evitando poluir projetos.

Depois disso:

```bash
cd qualquer-projeto
opencode
```

O Tide estará disponível globalmente.

## Estrutura

```txt
tide-protocol/
  install.sh
  bin/tide
  opencode/
    agents/
    commands/
    rules/
    skills/
```

## Status

Versão inicial: `0.1.0`.

Esta primeira versão implementa o bootstrap global do protocolo. MCP, integração profunda com code-review-graph e runtime real de patches por Wave ficam para próximas Waves.
