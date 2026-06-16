---
name: tide-project-commands
description: Descobrir, explicar e usar comandos específicos do projeto com segurança operacional.
license: MIT
compatibility: opencode
---

# tide-project-commands

Use quando o usuário pedir algo operacional ou quando o comando correto não for óbvio.

Procure comandos em:
- Makefile;
- package.json;
- pyproject.toml;
- README;
- scripts/;
- bin/;
- docker-compose.yml;
- .github/workflows/;
- AGENTS.md.

Ao propor comando, informe:
- finalidade;
- risco;
- timeout esperado;
- se precisa OK explícito;
- validação do resultado.
