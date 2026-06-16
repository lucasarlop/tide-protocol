# Release

Processo de release do Tide Protocol.

## Critérios para versão estável

Antes de marcar uma versão:

```bash
python3 -m py_compile bin/tide
python3 -m unittest discover -s tests -v
bash install.sh --dry-run
```

Critérios funcionais:

- `tide --version` bate com `VERSION`.
- `tide init` não altera `.gitignore` do projeto destino.
- Waves podem ser criadas, estacionadas, validadas, aprovadas e rejeitadas.
- Catálogo de comandos lista comandos descobertos e catalogados.
- Comandos sensíveis exigem OK explícito.
- Timeout retorna resultado inconclusivo.
- Agentes, comandos, skills e regras são instalados globalmente.

## Versionamento

Use Semantic Versioning.

- `0.x`: protocolo em evolução rápida.
- `1.0.0`: núcleo estável para uso diário.
- Patch releases corrigem bugs sem mudar semântica de Waves.

## Checklist

1. Atualizar `VERSION`.
2. Atualizar `CHANGELOG.md`.
3. Rodar CI local.
4. Revisar README.
5. Criar tag de versão.

## Política de segurança

O Tide não executa comandos sensíveis automaticamente. Qualquer operação marcada como `requires_ok` ou `safety` sensível exige confirmação explícita do supervisor.
