# Wave Policy

## Definição

Wave é uma unidade identificável de movimento sobre o software.

Toda Wave relevante deve ter arquivo em `.opencode/waves/<wave-id>/wave.md`.

## ID

Formato padrão:

```txt
TIDE-0001
```

A numeração é por projeto e cresce a partir do maior ID existente em `.opencode/waves/registry.json` ou diretórios existentes.

## Quando criar Wave

Crie Wave quando houver:

- alteração de código;
- operação com script, banco, SSH, geração ou reprocessamento;
- investigação longa;
- validação relevante;
- revisão ou correção com risco;
- qualquer trabalho que o supervisor possa querer aprovar, rejeitar ou acumular.

Não crie Wave para:

- resposta curta de dúvida simples;
- `/btw`;
- `/teach`;
- explicação sem mudança nem operação.

## Estados

- `running`: em andamento.
- `validated`: concluída com evidência suficiente.
- `parked`: estacionada para decisão posterior.
- `approved`: aceita pelo supervisor, mas não necessariamente commitada.
- `rejected`: revertida ou descartada.
- `committed`: commit realizado.
- `failed`: falhou sem recuperação segura.

## Checkpoint

Toda Wave relevante termina com checkpoint:

```md
## Wave concluída

Intenção:
- ...

Movimento feito:
- ...

Arquivos alterados:
- ...

Evidência:
- ...

Durabilidade:
- ...

Riscos/restos:
- ...

Opções:
- continuar
- ajustar
- estacionar
- /approve <wave-id>
- /reject <wave-id>
```

## Regras

- `approved` não significa `committed`.
- Commit só ocorre por pedido explícito do supervisor.
- Wave pode ficar `parked` enquanto outras Waves avançam.
- Rejeitar uma Wave nunca deve destruir mudanças de outra Wave silenciosamente.
- Se houver conflito entre Waves, pare e peça decisão.
