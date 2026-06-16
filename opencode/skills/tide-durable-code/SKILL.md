# Tide Durable Code

Use esta skill ao implementar ou revisar mudanças que afetam comportamento, configuração, ambiente, operação ou rotinas de longa duração.

## Checklist

- Env/config inválida gera mensagem específica?
- A mensagem orienta como corrigir?
- O erro aponta o nome da variável, comando ou recurso?
- O caminho de falha é compreensível?
- Há timeout/fallback quando envolve externo?
- Onde ajustar no futuro fica claro?
- A solução segue padrões atuais do projeto?
- Alguém novo conseguiria diagnosticar o problema?

## Não confundir com overengineering

Durabilidade não exige arquitetura grande. Exige comportamento claro, seguro e intuitivo.

## Resultado

Registre na Wave:

```md
Durabilidade:
- falha tratada:
- orientação ao operador:
- ajuste futuro:
- limites/timeouts:
```
