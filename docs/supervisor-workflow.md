# Supervisor Workflow

O Tide Protocol mantém o supervisor como autoridade final.

O agente pode agir dentro da fronteira da Wave, mas não deve transformar uma Wave em commit sem pedido explícito.

## Ciclo recomendado

```txt
pedido → Wave → execução → evidência → checkpoint → decisão do supervisor
```

Decisões possíveis:

```txt
continuar
estacionar
validar manualmente
ajustar
rejeitar
aprovar uma Wave
aprovar várias Waves juntas
```

## Criar Wave

```bash
tide wave create --title "Corrigir validação de config" --type code --risk medium
```

## Estacionar

```bash
tide wave park TIDE-0001 --note "Pronta para validação manual"
```

## Registrar evidência

```bash
tide wave validate TIDE-0001 \
  --summary "teste escopado passou" \
  --command "pytest tests/config -x" \
  --result "passed" \
  --status validated
```

## Aprovar

```bash
tide approve TIDE-0001
```

A mensagem de commit inclui o ID da Wave.

## Aprovar múltiplas Waves

```bash
tide approve TIDE-0001 TIDE-0002
```

Use quando as Waves fazem sentido juntas ou quando uma depende da outra.

## Rejeitar

```bash
tide reject TIDE-0001
```

O Tide aplica o reverse patch salvo. Se não aplicar limpo, ele para e não destrói alterações silenciosamente.

## Quando pedir checkpoint prévio

O agente deve parar antes de executar quando a Wave tocar:

- banco;
- produção;
- SSH;
- auth;
- permissões;
- secrets;
- deploy;
- CI/CD;
- migrations;
- reprocessamentos;
- scripts destrutivos;
- dependências novas;
- APIs públicas.

## Regra principal

Dentro da fronteira: aja.

Fora da fronteira: pare e peça checkpoint.
