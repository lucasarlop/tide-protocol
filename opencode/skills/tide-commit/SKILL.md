# Tide Commit

Use esta skill ao executar `/approve <wave-id>` ou quando o supervisor pedir commit explicitamente.

## Regras

- Commit nunca é automático.
- Não faça push.
- Não commite arquivos fora da Wave sem aviso e confirmação.
- Não inclua segredos.
- Não altere código durante a etapa de commit.

## Processo

1. Leia a Wave.
2. Mostre arquivos candidatos.
3. Verifique `git status`.
4. Stage apenas mudanças da Wave.
5. Rode `git diff --cached --check` quando possível.
6. Gere mensagem com ID da Wave.
7. Faça commit.
8. Registre hash.

## Mensagem

```txt
<type>(<scope>): <descrição> [TIDE-0000]

Wave: TIDE-0000
Resumo:
- ...

Evidência:
- ...
```

## Múltiplas Waves

Quando o supervisor pedir commit agrupado, inclua todos os IDs no corpo e escolha título que descreva o conjunto.
