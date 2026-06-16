# Tide Runtime Policy

Use esta skill antes de rodar testes, scripts, comandos de banco, SSH, geração, reprocessamento ou qualquer comando potencialmente longo.

## Classificar comando

- `quick`: esperado < 30s.
- `normal`: esperado < 2min.
- `slow`: esperado > 2min.
- `dangerous`: side effect relevante, produção, SSH, banco mutável, deploy, reprocessamento ou envio externo.

## Obrigatório

Registre:

```txt
comando:
classe:
timeout:
limite de silêncio:
critério de sucesso:
fallback:
precisa OK explícito:
```

## Regras

- Preferir teste escopado.
- Timeout é inconclusivo.
- Não repetir comando travado sem mudar algo.
- Dangerous exige OK explícito.
- Preferir dry-run quando existir.
