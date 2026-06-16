---
description: Estaciona uma Wave salvando snapshot sem decisão final.
agent: tide-steward
---

Estacione a Wave `$ARGUMENTS`.

Use:

```bash
tide wave park $ARGUMENTS
```

Regras:
- Não faça commit.
- Apenas salve snapshot e deixe a Wave pronta para decisão futura do supervisor.

Ao final, mostre status, arquivos capturados e próximos passos seguros.
