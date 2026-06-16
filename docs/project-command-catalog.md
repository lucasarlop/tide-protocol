# Project Command Catalog

O catálogo de comandos transforma rotinas específicas do projeto em capacidades claras para humanos e agentes.

O objetivo é permitir pedidos como:

```txt
analise o caso 123
regere o livro 456
rode a validação do módulo X
```

sem depender da memória humana sobre scripts, argumentos e timeouts.

## Localização

O Tide procura catálogos em:

```txt
.tide/commands.json
.tide.commands.json
tide.commands.json
.opencode/tide/commands.json
```

Além disso, descobre automaticamente scripts de:

```txt
package.json
Makefile
bin/
scripts/
tools/
```

## Exemplo

```json
{
  "commands": {
    "regenerate_book": {
      "description": "Regera um livro pelo ID.",
      "command": "./scripts/books/regenerate.sh --book-id {book_id}",
      "safety": "mutating",
      "requires_ok": true,
      "timeout": {
        "hard_sec": 600,
        "silence_sec": 60
      },
      "args": {
        "book_id": {
          "required": true,
          "description": "ID do livro"
        }
      },
      "validation": [
        "verificar status do livro",
        "verificar logs de erro",
        "confirmar artefato gerado"
      ]
    }
  }
}
```

## Safety

Valores recomendados:

```txt
read        consulta ou validação sem efeito colateral
local       comando local de baixo risco
mutating    altera arquivos, banco local, cache ou estado
production  toca produção
ssh         usa SSH
database    acessa banco diretamente
dangerous   pode destruir ou reprocessar dados
```

Qualquer comando com `requires_ok: true` ou safety sensível deve exigir OK explícito do supervisor antes de execução real.

## Uso

Listar:

```bash
tide project commands
```

Detalhar:

```bash
tide project command regenerate_book
```

Dry-run:

```bash
tide project run regenerate_book --arg book_id=123 --dry-run
```

Execução supervisionada:

```bash
tide project run regenerate_book --arg book_id=123 --yes
```

`--yes` representa autorização explícita do supervisor. Não use `--yes` por padrão.

## Validação

O agente deve registrar a evidência na Wave:

```bash
tide wave validate TIDE-0001 \
  --summary "regenerate_book dry-run concluiu" \
  --command "tide project run regenerate_book --arg book_id=123 --dry-run" \
  --result "passed" \
  --status validated
```
