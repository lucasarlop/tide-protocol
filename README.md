# Tide Protocol

Tide Protocol é um protocolo global para desenvolvimento assistido por IA no OpenCode, baseado em **Waves identificáveis**, fronteiras explícitas, código durável, validação proporcional ao risco e supervisão humana.

A metáfora central é simples: o software é o mar; cada Wave é um movimento limitado sobre ele. Algumas Waves são aprovadas, outras rejeitadas, outras ficam estacionadas até serem agrupadas em um commit maior.

## Princípios

- O código atual é a fonte da verdade.
- Cada Wave tem intenção, fronteira, evidência e checkpoint.
- O agente age com liberdade dentro da fronteira e para ao precisar cruzá-la.
- Código deve durar: falhar bem, orientar bem e ser intuitivo para manutenção futura.
- Validação deve ser proporcional ao risco.
- Revisores entram por risco, não por ritual.
- Commit nunca é automático; depende de `/approve <wave-id>` ou pedido explícito do supervisor.

## Conceitos

### Wave

Unidade identificável de movimento sobre o software.

Exemplo de ID:

```txt
TIDE-0001
```

Uma Wave pode investigar, implementar, operar, validar ou revisar. Ela tem representação local em arquivo dentro de `.opencode/waves/`, que deve ser ignorado pelo Git.

### Fronteira

Define o que a Wave pode tocar, quais comandos pode executar e quando deve parar.

### Evidência

Prova proporcional ao risco: teste, comando, diff, checklist, log, validação manual ou execução supervisionada.

### Supervisor

A pessoa responsável por aprovar, rejeitar, acumular ou commitar Waves.

## Comandos planejados

```txt
/waves
/wave <wave-id>
/approve <wave-id>
/reject <wave-id>
/btw <pergunta>
/teach <tema>
```

`/approve <wave-id>` deve criar commit com as alterações da Wave e mensagem contendo o ID. `/reject <wave-id>` deve desfazer apenas as alterações daquela Wave, sem destruir mudanças de outras Waves.

## Arquitetura

O Tide é pensado como instalação global:

- agentes e comandos globais do OpenCode;
- skills globais reutilizáveis;
- MCP opcional para comandos do projeto, snapshots de Waves, integração com code-review-graph e execução segura;
- estado local por projeto em `.opencode/waves/`.

## Estado deste repositório

Este repositório está na fundação inicial do protocolo. A primeira implementação prioriza agentes, comandos, rules, templates e o contrato das Waves antes do MCP completo.
