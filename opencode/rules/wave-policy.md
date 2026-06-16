# Wave Policy

Uma Wave é uma unidade identificável de movimento sobre o software.

## Identificação
- Use IDs sequenciais por projeto: `TIDE-0001`, `TIDE-0002`, ...
- Toda Wave relevante deve ter arquivo em `.opencode/waves/<id>/wave.md`.
- `.opencode/waves/` é estado operacional local e deve ficar no `.gitignore`.

## Tipos de Wave
- `question`: dúvida ou leitura do projeto; normalmente não altera arquivos.
- `investigation`: investigação estruturada com evidência.
- `code`: mudança de código.
- `operation`: comando, script, banco, SSH, geração ou reprocessamento.
- `review`: revisão especializada.
- `commit`: aprovação, rejeição ou organização de Waves.

## Estados
- `running`: em andamento.
- `parked`: parada ou concluída, mas sem approve/reject.
- `validated`: evidência suficiente, aguardando decisão.
- `committed`: aprovada e commitada.
- `rejected`: rejeitada e revertida.
- `failed`: falhou sem recuperação limpa.

## Regras
- A Wave deve declarar intenção, fronteira, durabilidade esperada e validação planejada.
- O agente pode agir livremente dentro da fronteira.
- Se precisar cruzar a fronteira, pare e peça decisão.
- Avançar para outra Wave sem approve/reject é permitido.
- `accepted` não é o mesmo que `committed`; commit depende de comando explícito.
