# Hardgates, restrições da Wave e pré-condições do plano

Este documento separa três conceitos que podem parecer semelhantes em uma sessão real do Tide, mas têm papéis diferentes.

## 1. Hardgate de protocolo

Hardgate é uma condição de parada obrigatória antes de executar uma ação sensível.

Exemplos:

- produção;
- deploy;
- CI/CD;
- SSH;
- banco de dados real;
- migrations;
- reprocessamento;
- scripts destrutivos;
- auth, permissões, tokens, secrets ou billing;
- dados reais;
- nova dependência;
- API pública;
- comando lento, mutável ou desconhecido;
- fronteira ambígua;
- validação inconclusiva.

Regra:

```txt
Se um hardgate aparecer, pare antes de executar e peça checkpoint explícito.
```

Hardgates são globais ao protocolo e não dependem apenas de uma Wave específica.

## 2. Restrição da Wave

Restrição da Wave é uma limitação deliberada do escopo atual. Algo pode ser proibido nesta Wave, mas permitido em uma Wave futura com fronteira e aprovação próprias.

Exemplos:

- nesta Wave, não usar Milvus real;
- nesta Wave, não usar Trino real;
- nesta Wave, não alterar `docker-compose.yml`;
- nesta Wave, não mudar contrato público da API;
- nesta Wave, não alterar ranking, apenas fallback;
- nesta Wave, tocar somente `backend/app/recommendations/engine.py` e testes relacionados.

Regra:

```txt
Se precisar cruzar uma restrição da Wave, pare e proponha nova Wave ou checkpoint.
```

Restrição da Wave não deve ser chamada de hardgate global quando for apenas limite local de escopo.

## 3. Pré-condição do plano

Pré-condição do plano é algo que precisa estar decidido antes de uma Wave futura, mas que não necessariamente bloqueia a Wave atual.

Exemplos:

- antes da Wave de infra local, decidir se Milvus será compose separado ou serviço externo;
- antes da Wave com dados reais, aprovar fonte, escopo, LGPD e owner;
- antes de produção, aprovar piloto, métricas, rollback e runbook;
- antes de indexação real, definir política de criação/recriação da coleção.

Regra:

```txt
Registre como pendência ou decisão futura. Não misture com hardgate da execução atual.
```

## Como o Tide deve comunicar

Em briefings e checkpoints, prefira separar assim:

```txt
Hardgates de protocolo:
- produção, deploy, banco real, secrets, dados reais, CI/CD, dependências novas.

Restrições desta Wave:
- não usar Milvus real;
- não usar Trino real;
- não alterar Docker;
- tocar somente arquivos X e Y.

Pré-condições para Waves futuras:
- ambiente Milvus local exige Wave própria;
- dados silver/Trino exigem aprovação própria;
- produção exige piloto e aceite operacional.
```

## O que o CLI garante hoje

O CLI garante mecanicamente principalmente:

- fronteira de snapshot por `--file` ou `--allow`;
- bloqueio de arquivos modificados fora da fronteira;
- limite de arquivos por `--max-files`;
- approve/reject supervisionado;
- proteção contra snapshot drift/overlap em approve.

O CLI não consegue, sozinho, provar que um comando não acessou Milvus real, Trino real, Docker, produção ou dados reais. Esses pontos dependem de:

- permissões do OpenCode;
- catálogo de comandos;
- prompts dos agentes;
- revisão humana;
- validações e logs da sessão.

## Nomes recomendados

Use os nomes com precisão:

- `Hardgate` para condição sensível que exige checkpoint antes de executar.
- `Restrição da Wave` para limite de escopo da Wave atual.
- `Pré-condição do plano` para decisão necessária antes de uma Wave futura.

Evite usar `hardgate` como sinônimo genérico de qualquer cuidado, pendência ou restrição.
