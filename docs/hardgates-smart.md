# Hardgates e SMART no Tide Protocol

O Tide herda a disciplina do `opencode-pack`, mas adapta o mecanismo para Waves.

No Tide, **hardgates** são condições que obrigam o agente a parar e pedir checkpoint. **SMART** é o critério mínimo para uma Wave estar bem definida antes de execução relevante.

## Hardgates

Um hardgate é uma barreira não negociável. Quando um hardgate aparece, o agente deve parar, explicar o risco e pedir decisão do supervisor antes de continuar.

### Hardgates técnicos

Pare antes de executar se a Wave tocar:

- produção;
- deploy;
- CI/CD;
- SSH;
- banco de dados;
- migrations;
- reprocessamento;
- scripts destrutivos;
- auth;
- permissões;
- tokens;
- secrets;
- billing;
- filas/workers críticos;
- cache compartilhado;
- API pública;
- nova dependência;
- alteração ampla em muitos arquivos;
- comando lento ou desconhecido.

### Hardgates de escopo

Pare se:

- o pedido ficou ambíguo;
- a fronteira inicial ficou pequena demais;
- a solução exige tocar arquivos fora do combinado;
- o agente descobriu outro problema relevante;
- a Wave virou refactor maior do que o previsto;
- a validação planejada não prova mais o risco real.

### Hardgates de validação

Pare se:

- teste trava;
- comando estoura timeout;
- saída é inconclusiva;
- ambiente necessário não existe;
- fixture/mock contradiz o comportamento real;
- validação exige acesso externo não autorizado;
- validação pode alterar dados reais.

### Hardgates de segurança

Pare se houver:

- segredo exposto;
- token real em logs;
- alteração de permissão;
- alteração de autenticação;
- bypass de validação;
- input externo não sanitizado;
- risco de vazamento de dados.

## SMART para Waves

Antes de executar uma Wave relevante, o agente deve garantir que ela é SMART.

### Specific

A Wave deve dizer exatamente o que será feito.

Ruim:

```txt
melhorar config
```

Bom:

```txt
melhorar erro quando env obrigatória estiver ausente ou vazia
```

### Measurable

A Wave deve ter evidência verificável.

Exemplos:

```txt
python3 -m unittest tests.test_config
pytest tests/config -x
tide project run validate_book --arg book_id=123 --dry-run
```

No Tide, validação executável deve preferir:

```bash
tide run --timeout-sec 120 --silence-sec 60 -- <comando>
```

ou:

```bash
tide project run <comando_catalogado> --dry-run
```

### Achievable

A Wave deve caber no budget/fronteira.

Exemplos de budget:

```txt
max-files: 3
risco: low
sem banco
sem nova dependência
sem alteração de API pública
```

Se não couber, divida em Waves menores ou peça checkpoint.

### Relevant

A Wave deve resolver o problema pedido, sem ampliar escopo.

Não transformar bug pequeno em:

```txt
refactor geral
nova arquitetura
mudança de framework
```

### Time-boxed

A Wave deve ter limite prático de execução/validação.

Exemplos:

```txt
teste escopado antes da suite completa
timeout hard de 120s
timeout por silêncio de 60s
checkpoint se investigação passar de 15min sem conclusão
```

## SMART no checkpoint final

O checkpoint final deve responder:

```txt
Wave: <id> — <título>
Status real: running|parked|validated|committed|rejected|failed
Specific: o que mudou
Measurable: evidência executada
Achievable: fronteira respeitada?
Relevant: resolveu o pedido?
Time-boxed: houve timeout ou execução longa?
Riscos/restos
Opções: continuar, ajustar, acumular, /reject, /approve
```

## Regra curta

```txt
Sem hardgate: aja dentro da fronteira.
Com hardgate: pare e peça checkpoint.
Wave sem SMART: não execute mudança relevante.
```
