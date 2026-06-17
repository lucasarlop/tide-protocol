# Commit Safety no Tide Protocol

O commit é a etapa mais sensível do fluxo Tide porque transforma uma Wave em histórico permanente do Git.

Por isso, o `tide-steward` deve ser simples/barato, mas o CLI precisa ser rígido.

## Regra principal

```txt
O subagente pode ser barato porque o CLI deve ser seguro.
```

## Approve seguro

Por padrão, `tide approve <id>` agora exige:

1. índice Git limpo antes do approve;
2. Wave com status `validated`;
3. arquivos registrados na Wave;
4. snapshot salvo em `wave.diff`;
5. diff atual dos arquivos igual ao snapshot salvo;
6. ausência de overlap com Waves ativas, salvo autorização explícita;
7. commit sem push.

## Bloqueios de segurança

O approve bloqueia quando:

- há mudanças staged antes do approve;
- a Wave não está `validated`;
- o snapshot salvo diverge do estado atual;
- a Wave não tem arquivos registrados;
- há outra Wave ativa tocando os mesmos arquivos;
- Waves selecionadas compartilham arquivos sem `--allow-overlap`.

## Flags de hardgate

Estas flags existem para casos excepcionais e exigem checkpoint explícito do supervisor:

```bash
tide approve TIDE-0001 --allow-unvalidated
tide approve TIDE-0001 --allow-snapshot-drift
tide approve TIDE-0001 --allow-overlap
```

Use somente quando o supervisor entendeu o risco e decidiu continuar.

## Finish seguro

Para evitar o padrão ruim `validate → park`, use:

```bash
tide wave finish TIDE-0001 \
  --summary "teste escopado passou" \
  --command "tide run --timeout-sec 120 --silence-sec 60 -- python3 -m unittest tests.test_config" \
  --result passed
```

Esse comando:

1. salva snapshot;
2. registra evidência;
3. deixa a Wave como `validated`.

Depois disso, `tide wave park TIDE-0001` é bloqueado, salvo `--force`.

## Reject seguro

`reject` também bloqueia se houver mudanças staged antes da operação.

O reverse patch é testado com `git apply -R --check` antes de alterar arquivos.

Se não aplicar limpo, o Tide para e não destrói alterações silenciosamente.

## Papel do tide-steward

O `tide-steward` deve:

- usar modelo barato/rápido;
- chamar apenas o CLI `tide`;
- nunca editar código;
- nunca fazer push;
- não misturar comandos manuais de Git com lógica própria;
- confirmar status final e working tree.

O steward não deve decidir sozinho ignorar validação, drift ou overlap. Esses casos são hardgates do supervisor.
