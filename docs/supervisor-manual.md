# Manual do Supervisor Tide

Este manual é voltado para quem usa o Tide Protocol como supervisor humano.

O supervisor não precisa conhecer todos os prompts internos dos agentes. Ele precisa entender como instalar, iniciar, pedir trabalho, revisar checkpoint, aprovar, rejeitar, lidar com hardgates e controlar risco/custo.

## Papel do supervisor

No Tide, o supervisor é a autoridade final.

O agente pode:

- criar Wave;
- investigar;
- implementar dentro da fronteira;
- rodar validação segura;
- registrar evidência;
- estacionar trabalho;
- sugerir próximos passos.

O agente não deve:

- commitar sem `/approve` ou pedido explícito;
- fazer push;
- cruzar hardgate sem checkpoint;
- executar comando sensível sem OK;
- esconder validação inconclusiva.

## Instalação recomendada

Para testar sem afetar projetos que já usam `opencode-pack`, use instalação isolada:

```bash
git clone https://github.com/lucasarlop/tide-protocol.git /tmp/tide-protocol
cd /tmp/tide-protocol
bash install.sh --force
```

Isso instala por padrão em:

```txt
~/.config/opencode-tide
```

No projeto que usará Tide:

```bash
cd meu-projeto
tide opencode
```

`tide opencode` roda `tide init` por padrão e abre o OpenCode com a config isolada.

Diagnóstico rápido:

```bash
tide doctor
```

Assim, projetos que usam a configuração global continuam rodando com:

```bash
opencode
```

## O que `tide init` faz

`tide init` prepara o repositório para Waves:

- exige que você esteja dentro de um repositório Git;
- cria `.opencode/waves/`;
- cria/garante `.opencode/waves/registry.json`;
- adiciona `.opencode/waves/` em `.git/info/exclude`;
- não altera `.gitignore`;
- não abre o OpenCode.

Normalmente você não precisa chamar isso manualmente, porque `tide opencode` já chama `tide init` por padrão.

## Configuração de modelo recomendada

O modo padrão é:

```txt
balanced-quality dinâmico
```

O Tide deve estimar o effort desejado (`medium`, `high`, `xhigh`) por Wave/subagente.

Com os modelos exibidos na sua configuração OpenCode, a recomendação prática é:

| Uso | Modelo | Variant |
|---|---|---|
| Sessão normal Tide | GPT-5.5 | medium ou high |
| Código importante | GPT-5.5 | high |
| Código crítico | GPT-5.5 Pro ou GPT-5.5 | xhigh |
| Segurança/dados/infra crítica | GPT-5.5 Pro ou GPT-5.5 | xhigh |
| Validação mecânica | GPT-5.5 Fast ou GPT-5.4 Fast | low/medium |
| Approve/reject/status | GPT-5.5 Fast ou GPT-5.4 Fast | low/medium |
| Dúvidas simples | GPT-5.5 Fast ou GPT-5.4 Fast | low/medium |

A troca real de modelo depende da configuração suportada pelo OpenCode. Quando não houver troca automática, o Tide deve registrar no briefing ao subagente o effort desejado.

## Modo fast

Você pode pedir:

```txt
modo fast
priorize velocidade
use fast
responda mais rápido
```

Modo fast significa:

- menos investigação ampla;
- menor Wave segura;
- menos reviewers quando não houver risco real;
- validação escopada antes de suite completa;
- checkpoint dizendo que fast mode foi usado.

Modo fast não desativa hardgates. Produção, banco, auth, secrets, deploy, permissões e comandos sensíveis continuam exigindo checkpoint.

## Como pedir uma tarefa

Você normalmente não precisa criar Wave manualmente.

Peça em linguagem natural:

```txt
@tide corrija a validação de DATABASE_URL para falhar com mensagem clara quando a env estiver ausente. Mantenha simples e valide com teste escopado.
```

O esperado:

```txt
1. tide cria/garante Wave;
2. tide define risco, fronteira, SMART, hardgates e effort;
3. tide delega código ao tide-runner;
4. tide delega validação ao tide-verifier;
5. tide registra evidência;
6. tide apresenta checkpoint.
```

## Como revisar um checkpoint

Um bom checkpoint deve conter:

```txt
Wave: TIDE-0001 — título
Status real
Movimento feito
Arquivos alterados
Evidência/validações
SMART
Durabilidade
Riscos/restos
Fast mode usado, se aplicável
Opções: continuar, ajustar, acumular, /reject, /approve
```

Antes de aprovar, confira:

- o pedido foi resolvido?
- a fronteira foi respeitada?
- a validação prova o comportamento?
- há risco de banco, produção, auth, permissões, deploy ou dados?
- houve timeout ou validação inconclusiva?
- os arquivos alterados fazem sentido?
- a Wave está `validated`?

## Aprovar

Quando estiver satisfeito:

```txt
/approve TIDE-0001
```

Ou, pelo CLI:

```bash
tide approve TIDE-0001
```

Approve deve:

- exigir Wave `validated` por padrão;
- exigir índice Git limpo antes do approve;
- checar snapshot salvo contra diff atual;
- bloquear overlap de Waves sem decisão explícita;
- criar commit com ID da Wave;
- marcar status como `committed`;
- não fazer push;
- confirmar working tree.

Flags de bypass só devem ser usadas após checkpoint explícito:

```bash
tide approve TIDE-0001 --allow-unvalidated
tide approve TIDE-0001 --allow-snapshot-drift
tide approve TIDE-0001 --allow-overlap
```

## Rejeitar

Quando a Wave não deve entrar:

```txt
/reject TIDE-0001
```

Ou:

```bash
tide reject TIDE-0001
```

Reject aplica o reverse patch salvo. Se não aplicar limpo, o Tide deve parar e pedir decisão.

## Acumular Waves

Você pode trabalhar em várias Waves antes de commitar:

```txt
TIDE-0001 validated
TIDE-0002 parked
TIDE-0003 validated
```

Aprovar juntas:

```txt
/approve TIDE-0001 TIDE-0003
```

Use isso quando as Waves fazem sentido no mesmo commit. Se houver overlap de arquivos, trate como hardgate.

## Hardgates do supervisor

Pare e peça explicação se aparecer:

- produção;
- banco;
- migration;
- auth;
- permissões;
- secrets;
- deploy;
- CI/CD;
- SSH;
- reprocessamento;
- script destrutivo;
- nova dependência;
- API pública;
- muitos arquivos além do previsto;
- validação inconclusiva.

Frase útil:

```txt
Pare. Faça checkpoint antes de executar. Qual é o risco, fronteira e validação segura?
```

## Controle de custo e velocidade

Use o princípio:

```txt
qualidade no código, economia no mecânico
```

Ajuste recomendado:

- código: high;
- código crítico: xhigh;
- validação mecânica: low/medium;
- approve/reject: low/medium;
- segurança/dados/infra: xhigh.

Se perceber excesso de chamadas:

```txt
Use fluxo enxuto. Sem reviewer salvo risco real. Uma validação escopada primeiro.
```

Se precisar de resposta rápida:

```txt
Use modo fast nesta Wave.
```

## Comandos úteis

```bash
tide opencode
tide open
tide doctor
tide wave list
tide wave show TIDE-0001
tide wave status TIDE-0001
tide wave diff TIDE-0001 --stat
tide wave files TIDE-0001
tide wave finish TIDE-0001 --summary "..." --command "tide run ..." --result passed
tide project commands
tide project command <nome>
tide project run <nome> --dry-run
tide run --timeout-sec 120 --silence-sec 60 -- <comando>
```

## Frases úteis para o supervisor

```txt
Crie uma Wave pequena e mantenha a fronteira restrita.
```

```txt
Use high para o runner porque essa mudança afeta código de produção.
```

```txt
Use xhigh para reviewer de segurança/dados/infra.
```

```txt
Use modo fast nesta Wave, mas preserve hardgates.
```

```txt
Não aprove ainda; estacione a Wave e me mostre diff, arquivos e evidência.
```

```txt
A validação está fraca. Adicione teste que prove o comportamento real.
```

```txt
Essa Wave cruzou a fronteira. Separe em outra Wave.
```
