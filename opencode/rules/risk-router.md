# Risk Router

O Tide não usa pipeline fixo. O agente principal decide o movimento pelo tipo de pedido, risco e fronteira.

## Classificação inicial

1. Dúvida sobre o projeto
   - Use `tide-guide`.
   - Não crie Wave se a resposta for curta e sem mudança.

2. Operação ou caso real
   - Crie Wave `operation`.
   - Use `tide-operator`.
   - Use `tide-verifier` para validação.

3. Mudança de código pequena
   - Crie Wave `code`.
   - Use `tide-runner`.
   - Use `tide-verifier`.

4. Mudança média
   - Crie Wave `code` com fronteira explícita.
   - Use `tide-runner`.
   - Use `tide-verifier`.
   - Acione reviewer específico se houver risco.

5. Mudança sensível
   - Faça checkpoint pré-implementação.
   - Crie Wave formal.
   - Acione subagentes necessários.

## Baixo risco

Critérios típicos:

- pedido claro;
- até 2 arquivos prováveis;
- sem banco, auth, infra, deploy ou dados reais;
- validação conhecida;
- sem nova dependência.

Fluxo:

```txt
tide -> tide-runner -> tide-verifier -> checkpoint
```

## Médio risco

Critérios típicos:

- 3 a 6 arquivos prováveis;
- comportamento relevante;
- validação não trivial;
- impacto limitado a módulo conhecido.

Fluxo:

```txt
tide -> Wave com fronteira -> tide-runner -> tide-verifier -> reviewer específico -> checkpoint
```

## Alto risco

Aciona quando toca:

- banco;
- migrations;
- auth;
- billing;
- permissões;
- secrets;
- produção;
- SSH;
- deploy;
- CI/CD;
- contrato público/API;
- filas/workers;
- script destrutivo ou reprocessamento;
- nova dependência;
- muitos arquivos;
- teste/comando lento ou desconhecido.

Fluxo:

```txt
tide -> checkpoint prévio -> Wave formal -> subagentes por fronteira -> validação -> checkpoint
```

## Regra central

O agente age dentro da fronteira. Se precisar cruzá-la, para e pede decisão.
