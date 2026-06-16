# Instalação

O Tide Protocol pode ser instalado de duas formas:

1. **isolado**, recomendado para testar sem afetar projetos que já usam outro protocolo;
2. **global**, recomendado depois que você decidir usar Tide como protocolo padrão da máquina.

## Instalação isolada recomendada para primeiro teste

Use um diretório de configuração separado do OpenCode:

```bash
git clone https://github.com/lucasarlop/tide-protocol.git /tmp/tide-protocol
cd /tmp/tide-protocol
bash install.sh --config-dir="$HOME/.config/opencode-tide" --bin-dir="$HOME/.local/bin"
```

Isso instala agentes, comandos, skills e regras do Tide em:

```txt
~/.config/opencode-tide/
```

sem mexer na configuração global padrão:

```txt
~/.config/opencode/
```

Para usar Tide em um projeto específico, abra o OpenCode apontando para a config isolada:

```bash
cd meu-projeto
tide init
OPENCODE_CONFIG_DIR="$HOME/.config/opencode-tide" opencode
```

Assim projetos que já usam `opencode-pack` continuam usando a configuração normal quando você roda apenas:

```bash
opencode
```

## Instalação global

Use quando quiser que Tide fique disponível por padrão em qualquer projeto:

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

## Como o uso deve acontecer

O usuário normalmente não precisa criar Waves manualmente.

O fluxo esperado é conversar com o agente:

```txt
@tide corrija a validação de DATABASE_URL para falhar com mensagem clara quando a env estiver ausente
```

O próprio agente deve:

1. rodar `tide init` se necessário;
2. criar a Wave com `tide wave create`;
3. executar dentro da fronteira;
4. estacionar com `tide wave park`;
5. registrar evidência com `tide wave validate`;
6. apresentar checkpoint.

Os comandos CLI existem para automação, auditoria e uso manual quando você quiser intervir.

## Atualizar

```bash
cd /tmp/tide-protocol
git pull
bash install.sh --force
```

Para atualizar a instalação isolada:

```bash
bash install.sh --force --config-dir="$HOME/.config/opencode-tide"
```

## MCP local

O MCP seguro é instalado em:

```txt
~/.config/opencode/tide-mcp/tide_mcp.py
```

Na instalação isolada, ele fica em:

```txt
~/.config/opencode-tide/tide-mcp/tide_mcp.py
```

Ele é context-only/planning-first. Não faz commit, não rejeita Wave e não executa comandos sensíveis.

Exemplo de configuração local para OpenCode:

```json
{
  "mcp": {
    "tide": {
      "type": "local",
      "command": ["python3", "/home/seu-usuario/.config/opencode-tide/tide-mcp/tide_mcp.py"],
      "enabled": true
    }
  }
}
```

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

Na instalação isolada, basta remover:

```txt
~/.config/opencode-tide
```

Em projetos, o estado local de Waves fica em `.opencode/waves/` e pode ser removido quando não houver Waves pendentes.
