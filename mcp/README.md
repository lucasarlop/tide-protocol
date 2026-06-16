# Tide MCP

Este diretório reserva o contrato inicial do MCP do Tide Protocol.

## Papel

O MCP Tide não deve conter agentes. Ele deve expor capacidades para os agentes globais do OpenCode.

## Tools planejadas

- `tide_wave_create`
- `tide_wave_status`
- `tide_wave_snapshot`
- `tide_wave_approve`
- `tide_wave_reject`
- `tide_project_profile`
- `tide_command_list`
- `tide_command_run`
- `tide_context_update`
- `tide_context_query`

## Integração com code-review-graph

O MCP Tide deve tratar code-review-graph como recurso opcional.

Comportamento esperado:

1. Se code-review-graph estiver disponível e configurado no projeto, usar para contexto vivo.
2. Se não estiver, continuar com leitura direta, grep, glob e análise local.
3. Não expor todas as tools do code-review-graph por padrão; preferir facade pequena do Tide.

## Segurança

- Comando dangerous exige OK explícito.
- Execução deve seguir runtime policy.
- Snapshots e patches de Wave não devem ser versionados.
- O MCP não deve chamar outro OpenCode nem criar loop de agentes.
