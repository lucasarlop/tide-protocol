# Instalação

O Tide Protocol foi desenhado para ser instalado uma vez por máquina e ficar disponível em qualquer projeto que use OpenCode.

## Instalação global

```bash
git clone https://github.com/lucasarlop/tide-protocol.git /tmp/tide-protocol
cd /tmp/tide-protocol
bash install.sh
```

O instalador copia:

```txt
opencode/agents   -> ~/.config/opencode/agents
opencode/commands -> ~/.config/opencode/commands
opencode/skills   -> ~/.config/opencode/skills
opencode/rules    -> ~/.config/opencode/rules/tide
mcp               -> ~/.config/opencode/tide-mcp
bin/tide          -> ~/.local/bin/tide
```

## Validar instalação

```bash
tide --version
bash install.sh --dry-run
```

Em um projeto:

```bash
cd meu-projeto
tide init
opencode
```

`tide init` cria `.opencode/waves/` e ignora esse diretório localmente via `.git/info/exclude`. Ele não altera `.gitignore`.

## Atualizar

```bash
cd /tmp/tide-protocol
git pull
bash install.sh --force
```

## MCP local

O MCP seguro é instalado em:

```txt
~/.config/opencode/tide-mcp/tide_mcp.py
```

Ele é context-only/planning-first. Não faz commit, não rejeita Wave e não executa comandos sensíveis.

Exemplo de configuração local para OpenCode:

```json
{
  "mcp": {
    "tide": {
      "type": "local",
      "command": ["python3", "~/.config/opencode/tide-mcp/tide_mcp.py"],
      "enabled": true
    }
  }
}
```

Se o cliente não expandir `~`, substitua pelo caminho absoluto do seu usuário.

## Desinstalação manual

Remova os arquivos globais do Tide em:

```txt
~/.config/opencode/agents/tide*.md
~/.config/opencode/commands/*
~/.config/opencode/skills/tide-*
~/.config/opencode/rules/tide
~/.config/opencode/tide-mcp
~/.local/bin/tide
```

Em projetos, o estado local de Waves fica em `.opencode/waves/` e pode ser removido quando não houver Waves pendentes.
