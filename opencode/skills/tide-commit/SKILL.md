---
name: tide-commit
description: Aprovar Waves com commits seguros, incluindo o ID da Wave e sem push automático.
license: MIT
compatibility: opencode
---

# tide-commit

Use somente quando o supervisor pedir `/approve <wave-id>` ou autorização equivalente.

## Regras
- Não faça push.
- Não edite código durante commit.
- Stage apenas arquivos registrados na Wave.
- Inclua o ID da Wave na mensagem.
- Se mudanças de Waves diferentes estiverem misturadas, pare.
- Se a Wave não tem snapshot/files.json, peça para estacionar/snapshot antes.

Mensagem padrão:

```txt
chore(tide): <descrição> [TIDE-000N]

Wave: TIDE-000N
```
