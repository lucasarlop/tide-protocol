# Tide MCP

O Tide MCP é a camada plugável de contexto do Tide Protocol.

Estado atual:
- `mcp/tide_mcp.py` define o contrato seguro inicial.
- Ações que mudam o projeto continuam no CLI `tide` e nos comandos globais do OpenCode.
- O MCP deve expor perfil do projeto, Waves, catálogo de comandos e planos de uso.

Tools planejadas:

```txt
tide_project_profile
tide_wave_list
tide_wave_show
tide_commands_list
tide_command_plan
tide_context_status
```

Decisão de segurança:

O servidor MCP começa como camada de contexto e planejamento. Operações sensíveis continuam exigindo confirmação explícita do supervisor.
