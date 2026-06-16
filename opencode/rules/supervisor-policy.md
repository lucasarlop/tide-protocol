# Supervisor Policy

O supervisor decide se uma Wave será aprovada, rejeitada, acumulada ou continuada.

## Checkpoint
Ao concluir ou estacionar uma Wave, entregue:

- ID e título;
- movimento feito;
- arquivos alterados;
- evidência obtida;
- validação manual sugerida;
- riscos/restos;
- opções: continuar, ajustar, rejeitar, aprovar/commitar ou acumular.

## Commit
- Commit nunca é automático.
- Commit só acontece com `/approve <wave-id>` ou pedido explícito equivalente.
- `/approve` deve incluir o ID da Wave na mensagem de commit.
- `/reject` deve preservar mudanças de outras Waves e parar em conflito.
