# Tide Wave

Use esta skill ao criar, concluir, estacionar ou retomar Waves.

## Criar Wave

1. Descubra o próximo ID `TIDE-XXXX`.
2. Crie `.opencode/waves/<id>/wave.md` usando `templates/wave.md`.
3. Defina intenção, tipo, risco e fronteira.
4. Registre validação planejada.
5. Não crie Wave para pergunta curta ou explicação isolada.

## Encerrar Wave

Preencha checkpoint:

```md
## Wave <id>

Status:
Resumo:
Arquivos:
Evidência:
Durabilidade:
Riscos/restos:
Opções:
- continuar
- ajustar
- estacionar
- /approve <id>
- /reject <id>
```

## Estacionar

Use `parked` quando a Wave terminou o movimento atual, mas o supervisor ainda não aprovou nem rejeitou.

## Regra

Wave é estado operacional local, não histórico versionado.
