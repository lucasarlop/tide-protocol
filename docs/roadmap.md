# Tide Protocol Roadmap

Este roadmap organiza a implementação do Tide Protocol em Waves. O objetivo é preservar o modelo boundary-first: cada entrega deve ter fronteira clara, evidência e checkpoint.

## TIDE-0005 — Installer global e configuração OpenCode

Objetivo: tornar a instalação global realmente plugável em qualquer projeto.

Escopo:
- garantir instalação de `tide` em `~/.local/bin`;
- instalar agentes, comandos, skills e regras em `~/.config/opencode`;
- validar `install.sh --dry-run` e `install.sh --force`;
- documentar instalação e atualização;
- preparar ponto de extensão para MCP sem ativar por padrão.

Fora de escopo:
- implementar MCP completo;
- instalar `code-review-graph` automaticamente.

## TIDE-0006 — MCP Tide mínimo

Objetivo: expor o Tide como MCP local via stdio, sem substituir agentes OpenCode.

Ferramentas desejadas:
- `tide_wave_list`;
- `tide_wave_show`;
- `tide_wave_create`;
- `tide_wave_park`;
- `tide_project_commands`;
- `tide_project_command`;
- `tide_project_run_dry`.

Fronteira:
- MCP não deve fazer commit;
- MCP não deve executar comando mutável real sem uma segunda Wave de segurança;
- MCP não deve chamar outro OpenCode.

## TIDE-0007 — Código Vivo com code-review-graph

Objetivo: integrar contexto atual do código sem transformar histórico de specs em fonte da verdade.

Escopo:
- detectar se `code-review-graph` está instalado;
- detectar se o projeto tem grafo ativo;
- sugerir build/update quando faltar;
- expor comandos Tide para contexto vivo;
- documentar fallback quando CRG não existir.

Fora de escopo:
- tornar CRG dependência obrigatória.

## TIDE-0008 — Project command catalog avançado

Objetivo: consolidar comandos operacionais específicos por projeto.

Escopo:
- suportar `.tide/commands.json` com schema validado;
- suportar comandos com argumentos obrigatórios/opcionais;
- suportar `dry_run_command` separado de `command`;
- registrar validações esperadas;
- melhorar mensagens para comandos sensíveis.

## TIDE-0009 — Wave isolation avançado

Objetivo: melhorar approve/reject quando Waves se sobrepõem.

Escopo:
- detectar conflito por arquivo e por hunk quando possível;
- permitir approve agrupado seguro;
- explicar quando a reversão isolada não é segura;
- preservar a regra: nunca destruir mudanças de outra Wave silenciosamente.

## TIDE-0010 — CI e release

Objetivo: tornar o Tide instalável e verificável com confiança.

Escopo:
- adicionar GitHub Actions para testes;
- validar `python3 -m unittest discover -s tests -v`;
- validar `bash install.sh --dry-run`;
- publicar instruções de release;
- revisar versionamento semântico.
