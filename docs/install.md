# Instalação

O Tide Protocol pode ser instalado de duas formas:

1. **isolado**, recomendado para testar sem afetar projetos que já usam outro protocolo;
2. **global**, recomendado depois que você decidir usar Tide como protocolo padrão da máquina.

A partir do instalador atual, o modo isolado é o padrão seguro.

## Instalação isolada recomendada

Use um diretório de configuração separado do OpenCode:

```bash
git clone https://github.com/lucasarlop/tide-protocol.git /tmp/tide-protocol
cd /tmp/tide-protocol
bash install.sh --force
```

Por padrão, isso instala agentes, comandos, skills, regras e MCP do Tide em:

```txt
~/.config/opencode-tide/
```

sem mexer na configuração global padrão:

```txt
~/.config/opencode/
```

Também instala:

```txt
~/.local/bin/tide      launcher Tide
~/.local/bin/tide-cli  CLI operacional real
~/.local/bin/tide.config  config isolada usada pelo launcher
```

Para usar Tide em um projeto específico:

```bash
cd meu-projeto
tide opencode
```

`tide opencode` roda `tide init` por padrão e abre o OpenCode com:

```bash
OPENCODE_CONFIG_DIR="$HOME/.config/opencode-tide"
```

Assim projetos que já usam `opencode-pack` continuam usando a configuração normal quando você roda apenas:

```bash
opencode
```

## Usos do launcher

Abrir OpenCode com config isolada e inicializar Waves:

```bash
tide opencode
```

Abrir sem rodar `tide init`:

```bash
tide opencode --no-init
```

Usar outra config:

```bash
tide opencode --config-dir "$HOME/.config/opencode-tide-quality"
```

Alias curto:

```bash
tide open
```

Diagnosticar instalação e projeto:

```bash
tide doctor
```

Comandos normais continuam funcionando:

```bash
tide wave list
tide approve TIDE-0001
```

Internamente, o launcher delega comandos operacionais para `tide-cli`.

## Instalação global

Use quando quiser que Tide fique disponível por padrão em qualquer projeto.

A instalação global exige flag explícita:

```bash
git clone https://github.com/lucasarlop/tide-protocol.git /tmp/tide-protocol
cd /tmp/tide-protocol
bash install.sh --global --force
```

Isso copia:

```txt
opencode/agents   -> ~/.config/opencode/agents
opencode/commands -> ~/.config/opencode/commands
opencode/skills   -> ~/.config/opencode/skills
opencode/rules    -> ~/.config/opencode/rules/tide
mcp               -> ~/.config/opencode/tide-mcp
bin/tide-cli      -> ~/.local/bin/tide-cli
bin/tide-launcher -> ~/.local/bin/tide
```

Sem `--global`, o instalador não escreve em `~/.config/opencode`.

## Validar instalação

```bash
tide --version
tide doctor
bash install.sh --dry-run
```

Em um projeto com instalação isolada:

```bash
cd meu-projeto
tide opencode
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
4. validar com `tide run` ou `tide project run`;
5. finalizar com `tide wave finish` quando houver evidência suficiente;
6. apresentar checkpoint.

Os comandos CLI existem para automação, auditoria e uso manual quando você quiser intervir.

## Atualizar

Para atualizar a instalação isolada:

```bash
cd /tmp/tide-protocol
git pull
bash install.sh --force
```

Para atualizar instalação global:

```bash
cd /tmp/tide-protocol
git pull
bash install.sh --global --force
```

## MCP local

Na instalação isolada, o MCP seguro fica em:

```txt
~/.config/opencode-tide/tide-mcp/tide_mcp.py
```

Na instalação global, fica em:

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
      "command": ["python3", "/home/seu-usuario/.config/opencode-tide/tide-mcp/tide_mcp.py"],
      "enabled": true
    }
  }
}
```

## Desinstalação manual

Na instalação isolada, remova:

```txt
~/.config/opencode-tide
~/.local/bin/tide
~/.local/bin/tide-cli
~/.local/bin/tide.config
```

Na instalação global, remova:

```txt
~/.config/opencode/agents/tide*.md
~/.config/opencode/commands/*
~/.config/opencode/skills/tide-*
~/.config/opencode/rules/tide
~/.config/opencode/tide-mcp
~/.local/bin/tide
~/.local/bin/tide-cli
~/.local/bin/tide.config
```

Em projetos, o estado local de Waves fica em `.opencode/waves/` e pode ser removido quando não houver Waves pendentes.
