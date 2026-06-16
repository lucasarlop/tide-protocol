---
description: Executa um comando catalogado do projeto com runtime policy.
---

Use `tide project run` para executar um comando catalogado.

Regras:
- Use dry-run antes de comandos operacionais relevantes.
- Confirmação explícita só quando o supervisor aprovou claramente.
- Não execute comando mutável, dangerous, banco, SSH, produção ou reprocessamento sem OK explícito.
- Respeite timeout e silence timeout do catálogo.
- Resultado com timeout é inconclusivo, não sucesso nem falha da implementação.
