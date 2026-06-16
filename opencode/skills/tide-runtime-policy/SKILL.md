---
name: tide-runtime-policy
description: Executar testes e comandos com timeout, limite de silêncio, fallback e classificação de risco.
license: MIT
compatibility: opencode
---

# tide-runtime-policy

Classifique comandos antes de rodar:

- quick: esperado < 30s;
- normal: esperado < 2min;
- slow: esperado > 2min;
- dangerous: side effect real, banco, SSH, produção, deploy, reprocessamento ou script destrutivo.

## Regras
- Use teste escopado antes de suite completa.
- Todo comando slow deve ter timeout.
- Dangerous exige OK explícito.
- Timeout é validação inconclusiva.
- Não repita comando travado sem mudar hipótese, escopo ou ambiente.

Registre comando exato, resultado e evidência.
