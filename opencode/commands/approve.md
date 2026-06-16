---
description: Aprova e commita uma Wave específica
---

Aprove a Wave informada em `$ARGUMENTS`.

Regras:

- Só prossiga se houver um único `wave-id` claro ou uma lista explícita de IDs.
- Leia `.opencode/waves/<wave-id>/wave.md`.
- Confira status, evidência e alterações atribuídas à Wave.
- Stage apenas as alterações da Wave.
- Gere commit message incluindo o ID da Wave.
- Faça commit.
- Não faça push.
- Se houver risco de misturar alterações de outras Waves, pare e explique.
- Se o patch não aplicar limpo, pare e explique.

Formato da mensagem:

```txt
<type>(<scope>): <descrição curta> [TIDE-0000]

Wave: TIDE-0000
Resumo:
- ...

Evidência:
- ...
```

Finalize com hash do commit e status da Wave.
