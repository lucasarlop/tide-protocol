# Tide Project Commands

Use esta skill ao responder ou executar pedidos que dependem de comandos específicos do projeto.

## Onde procurar comandos

- Makefile
- package.json
- pyproject.toml
- composer.json
- scripts/
- bin/
- tools/
- docker-compose.yml
- README.md
- AGENTS.md
- docs/
- .github/workflows/

## Como responder

Quando o usuário pedir algo como "analise este caso" ou "regere o livro X":

1. Descubra o comando mais específico.
2. Explique o que ele faz.
3. Classifique pela runtime policy.
4. Prefira dry-run.
5. Peça OK explícito se for dangerous.
6. Registre evidência na Wave.

## Catálogo futuro

O MCP Tide poderá expor comandos catalogados por projeto, com nome, descrição, args, safety, timeout e validação.
