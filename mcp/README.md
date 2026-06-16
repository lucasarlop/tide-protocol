# Tide MCP

O Tide MCP é a camada plugável de contexto do Tide Protocol.

Estado atual:
- `mcp/tide_mcp.py` implementa um servidor MCP stdio seguro.
- O servidor expõe contexto, Waves, catálogo de comandos e planos de uso.
- Ações que mudam o projeto continuam no CLI `tide` e nos comandos globais do OpenCode.

Tools disponíveis:

```txt
tide_project_profile
tide_wave_list
tide_wave_show
tide_commands_list
tide_command_plan
tide_context_status
```

Resource disponível:

```txt
tide://project/profile
```

Prompt disponível:

```txt
tide-wave
```

## Instalação

Após `bash install.sh`, o módulo é copiado para:

```txt
~/.config/opencode/tide-mcp/tide_mcp.py
```

## Segurança

O MCP é context-only/planning-first. Ele não faz commit, não rejeita Wave e não substitui o supervisor.

Operações continuam passando pelo CLI `tide`, com `safety`, `requires_ok`, timeout e validação.
