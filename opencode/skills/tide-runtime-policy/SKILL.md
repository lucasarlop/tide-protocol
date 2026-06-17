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
- Toda validação executável deve preferir `tide run` ou `tide project run`.
- Quando souber o comando escopado, passe ao verifier o comando exato já envelopado com `tide run` e timeout.
- Prefira `python3` a `python` quando não houver comando catalogado.
- Não troque teste escopado seguro por suíte maior apenas porque existe comando catalogado.
- Todo comando slow deve ter timeout.
- Dangerous exige OK explícito.
- Timeout é validação inconclusiva.
- Não repita comando travado sem mudar hipótese, escopo ou ambiente.

Registre comando exato, resultado e evidência.
