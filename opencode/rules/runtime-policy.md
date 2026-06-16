# Command Runtime Policy

Todo comando potencialmente longo precisa de timeout, limite de silêncio, critério de sucesso e fallback.

## Classes

- `quick`: esperado abaixo de 30s.
- `normal`: esperado abaixo de 2min.
- `slow`: esperado acima de 2min ou com dependência externa.
- `dangerous`: banco mutável, produção, SSH, deploy, reprocessamento, envio externo ou script com side effect relevante.

## Regras

1. Preferir validação escopada antes de suíte completa.
2. Nunca rodar comando potencialmente longo sem timeout explícito ou limite de parada.
3. Se ficar sem output além do limite, interrompa e analise.
4. Timeout não é falha do código; é validação inconclusiva.
5. Não repetir comando travado sem mudar hipótese, escopo ou ambiente.
6. Comando `dangerous` exige OK explícito do supervisor.
7. `tide-verifier` pode rodar comandos, mas não edita código.
8. `tide-operator` deve preferir dry-run quando existir.

## Resultado esperado

Registre em toda Wave:

```txt
comando:
classe:
timeout:
resultado:
evidência:
inconclusivo: sim|não
fallback aplicado:
```
