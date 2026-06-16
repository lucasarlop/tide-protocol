---
description: Rejeita uma Wave e desfaz suas alterações
---

Rejeite a Wave informada em `$ARGUMENTS`.

Regras:

- Leia `.opencode/waves/<wave-id>/wave.md`.
- Identifique as alterações atribuídas à Wave.
- Tente reverter apenas essas alterações.
- Atualize status para `rejected`.
- Não destrua mudanças de outras Waves.
- Não apague arquivos não rastreados sem confirmação explícita.
- Se houver conflito ou risco de perda de trabalho, pare e explique as opções.

Finalize com:

```md
Wave rejeitada: <id>
Arquivos revertidos:
- ...
Conflitos ou riscos:
- ...
```
