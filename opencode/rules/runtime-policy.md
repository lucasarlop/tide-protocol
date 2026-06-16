# Command Runtime Policy

Todo comando potencialmente longo deve ter:

- classificação: `quick`, `normal`, `slow` ou `dangerous`;
- timeout esperado;
- timeout máximo;
- limite de silêncio;
- critério de sucesso;
- critério de resultado inconclusivo;
- fallback.

## Regras
- Prefira teste escopado antes de suite completa.
- Nunca repita comando travado sem mudar hipótese, escopo ou ambiente.
- Timeout não significa falha do código; significa validação inconclusiva.
- Comando de banco, SSH, produção, reprocessamento ou side effect real exige OK explícito.
- O verifier não edita código.
- Registre comando exato, resultado e se houve timeout.
