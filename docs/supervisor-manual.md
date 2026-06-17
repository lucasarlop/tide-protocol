# Manual do Supervisor Tide

Este manual é voltado para quem usa o Tide Protocol como supervisor humano.

O supervisor não precisa conhecer todos os prompts internos dos agentes. Ele precisa entender como instalar, iniciar, pedir trabalho, revisar checkpoint, aprovar, rejeitar e controlar risco/custo.

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

## Instalação recomendada para primeiro uso

Para testar sem afetar projetos que já usam `opencode-pack`, use instalação isolada:

```bash
git clone https://github.com/lucasarlop/tide-protocol.git /tmp/tide-protocol
cd /tmp/tide-protocol
bash install.sh --config-dir="$HOME/.config/opencode-tide" --bin-dir="$HOME/.local/bin" --force
```

No projeto que usará Tide:

```bash
cd meu-projeto
tide init
OPENCODE_CONFIG_DIR="$HOME/.config/opencode-tide" opencode
```

Assim, projetos que usam a configuração global continuam rodando com:

```bash
opencode
```

## Configuração de modelo recomendada

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

O Tide deve estimar o effort desejado (`medium`, `high`, `xhigh`) e registrar isso no briefing ao subagente. A troca real de modelo depende da configuração suportada pelo OpenCode.

## Como pedir uma tarefa

Você normalmente não precisa criar Wave manualmente.

Peça em linguagem natural:

```txt
@tide corrija a validação de DATABASE_URL para falhar com mensagem clara quando a env estiver ausente. Mantenha simples e valide com teste escopado.
```

O esperado:

```txt
1. tide cria/garante Wave;
2. tide define risco, fronteira e effort;
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
Opções: continuar, ajustar, acumular, /reject, /approve
```

Antes de aprovar, confira:

- o pedido foi resolvido?
- a fronteira foi respeitada?
- a validação prova o comportamento?
- há risco de banco, produção, auth, permissões, deploy ou dados?
- houve timeout ou validação inconclusiva?
- os arquivos alterados fazem sentido?

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

- criar commit com ID da Wave;
- marcar status como `committed`;
- não fazer push;
- confirmar working tree.

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

Use isso quando as Waves fazem sentido no mesmo commit.

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
- muitos arquivos além do previsto.

Frase útil:

```txt
Pare. Faça checkpoint antes de executar. Qual é o risco, fronteira e validação segura?
```

## Controle de custo

Use o perfil mental:

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

## Comandos úteis

```bash
tide wave list
tide wave show TIDE-0001
tide wave status TIDE-0001
tide wave diff TIDE-0001 --stat
tide wave files TIDE-0001
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
Não aprove ainda; estacione a Wave e me mostre diff, arquivos e evidência.
```

```txt
A validação está fraca. Adicione teste que prove o comportamento real.
```

```txt
Essa Wave cruzou a fronteira. Separe em outra Wave.
```
