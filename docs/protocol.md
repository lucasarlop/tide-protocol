# Tide Protocol

## Definição

Tide Protocol é um protocolo de desenvolvimento assistido por IA para OpenCode. Ele organiza o trabalho em Waves identificáveis, com fronteiras explícitas, validação proporcional ao risco e supervisão humana.

O protocolo não é spec-first nem pipeline-first. Ele é boundary-first: o agente principal decide o próximo movimento pelo risco, pela fronteira e pela intenção da tarefa.

## Metáfora

O software é o mar: uma entidade única, viva e atual. Uma Wave é um movimento sobre esse mar. Cada Wave faz seu papel e pode ser aceita, rejeitada, estacionada ou agrupada com outras Waves.

## Fonte da verdade

A fonte da verdade é sempre:

1. código atual;
2. git status/diff atual;
3. validações reais;
4. contexto vivo do projeto, quando disponível.

Histórico de specs e decisões não é mantido por padrão.

## Wave

Uma Wave é uma unidade limitada, identificável e supervisionável de trabalho.

Toda Wave deve ter:

- `id`;
- intenção;
- fronteira;
- risco;
- tipo;
- evidência esperada ou executada;
- status;
- checkpoint para o supervisor.

Tipos iniciais:

- `question` — investigação ou resposta sobre o projeto;
- `operation` — comando, script, banco, SSH, reprocessamento, geração;
- `code` — mudança de código;
- `review` — revisão de algo já alterado;
- `validation` — prova, teste, checklist ou comando;
- `commit` — preparação/aprovação de commit.

Status iniciais:

- `running` — em andamento;
- `validated` — tem evidência suficiente;
- `parked` — estacionada, nem aprovada nem rejeitada;
- `approved` — aceita pelo supervisor, mas não necessariamente commitada;
- `rejected` — revertida ou descartada;
- `committed` — commit realizado;
- `failed` — falhou sem recuperação segura.

Regra essencial:

```txt
approved != committed
```

## Fronteira

A fronteira define o que a Wave pode fazer.

Inclua quando relevante:

- arquivos permitidos;
- arquivos proibidos;
- máximo de arquivos;
- dependências permitidas;
- comandos permitidos;
- comandos proibidos;
- ambientes permitidos;
- condição de parada.

O agente pode agir livremente dentro da fronteira. Ao precisar cruzá-la, deve parar e pedir decisão.

## Evidência

Toda mudança relevante precisa de evidência proporcional ao risco.

Exemplos:

- teste automatizado;
- typecheck;
- lint;
- build;
- comando operacional;
- dry-run;
- diff revisado;
- checklist manual;
- logs;
- validação supervisionada.

Timeout ou comando travado é evidência inconclusiva, não aprovação.

## Supervisor

O supervisor pode, a qualquer momento:

- continuar para outra Wave;
- pedir ajuste;
- estacionar;
- aprovar;
- rejeitar;
- agrupar Waves;
- commitar.

Commit nunca é automático.

## Comandos centrais

```txt
/waves
/wave <wave-id>
/approve <wave-id>
/reject <wave-id>
```

`/approve` deve criar commit com o ID da Wave na mensagem. `/reject` deve tentar desfazer apenas as alterações daquela Wave e parar se houver risco de afetar outra Wave.
