# Architecture

## Visão geral

O Tide Protocol usa uma arquitetura híbrida.

```txt
OpenCode
  agentes globais Tide
  comandos slash globais
  skills globais
  MCP Tide opcional

Projeto atual
  código
  git status/diff
  .opencode/waves/ ignorado
  comandos/scripts do projeto
  code-review-graph opcional
```

## Por que não colocar agentes dentro do MCP

MCP é a camada de tools, resources e prompts. Ele fornece capacidades e contexto para o host de IA. Agentes, permissões, subagentes e orquestração continuam sendo responsabilidade do OpenCode.

Arquitetura evitada:

```txt
OpenCode do projeto -> MCP -> outro sistema de agentes
```

Arquitetura adotada:

```txt
OpenCode do projeto
  -> agentes Tide globais
  -> skills Tide globais
  -> MCP Tide para capacidades
```

## Instalação global

A instalação preferida é global, para evitar poluir projetos.

Destino sugerido:

```txt
~/.config/opencode/agents/
~/.config/opencode/commands/
~/.config/opencode/skills/
~/.config/opencode/opencode.json
```

Estado por projeto:

```txt
.opencode/waves/
```

Esse diretório deve ser ignorado pelo Git.

## MCP Tide

O MCP Tide deve expor poucas ferramentas bem descritas.

Ferramentas planejadas:

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

## Código Vivo

Código Vivo significa contexto atualizado sobre o projeto atual. O Tide deve tratar como fonte de verdade:

1. código atual;
2. git status/diff;
3. validações reais;
4. code-review-graph quando disponível.

O code-review-graph é recomendado, mas não obrigatório. O Tide deve continuar funcionando com read/grep/list quando ele não existir.

## Regras de segurança

- MCP executa capacidades; agente decide.
- Comando de banco, SSH, produção, reprocessamento ou side effect real exige aprovação explícita.
- Tools de contexto devem ser poucas para reduzir ruído.
- O verifier pode rodar comandos, mas não edita código.
- Reviewers revisam fronteiras específicas, não estilo subjetivo.
