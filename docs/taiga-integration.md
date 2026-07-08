# Integração Taiga

A integração Taiga é opcional e genérica. Ela não deve conter nada específico de empresa, órgão, time ou projeto.

Taiga é a trilha organizacional externa. Wave é a unidade técnica local.

## Princípio

O Tide não usa Taiga por padrão.

Taiga só entra no fluxo quando:

- o supervisor sinaliza explicitamente;
- a Wave já está vinculada ao Taiga;
- `taiga.enabled=true` está registrado nos metadados locais da Wave.

Depois de ativado para uma Wave, o supervisor não deve precisar pedir checkpoints manuais. O Tide pode sincronizar eventos naturais da Wave.

## Casos suportados

### 1. Brainstorming maduro para Taiga

Fluxo:

```txt
Supervisor discute e amadurece plano no Tide
↓
Supervisor diz: "pode levar para o Taiga"
↓
tide-taiga transforma em item organizacional
↓
Taiga recebe objetivo, escopo, fora de escopo, critérios de aceite, validação e riscos
↓
Wave fica vinculada ao item
```

Comando determinístico equivalente:

```bash
tide taiga create-from-wave TIDE-0005 --kind task --yes
```

### 2. Atividade existente no Taiga para Wave

Fluxo:

```txt
Supervisor: "quero realizar a atividade #231 do Taiga"
↓
tide-taiga lê/avalia a atividade
↓
se não estiver madura, propõe ajuste
↓
se autorizado, atualiza o Taiga
↓
Tide cria Wave vinculada
↓
trabalho técnico segue normalmente
```

Comandos determinísticos equivalentes:

```bash
tide taiga get --kind task --ref 231
tide taiga maturity --kind task --ref 231
tide taiga link TIDE-0005 --kind task --ref 231
```

Critérios de maturidade:

- objetivo claro;
- escopo claro;
- fora de escopo ou limite explícito;
- critérios de aceite;
- validação esperada;
- riscos/hardgates conhecidos;
- tamanho compatível com uma Wave.

### 3. Trabalho local para registro no Taiga

Fluxo:

```txt
Trabalho ocorreu localmente
↓
Supervisor: "registre esse processo no Taiga"
↓
tide-taiga usa Wave, code-report, validações e commit quando existirem
↓
Taiga recebe registro consolidado
```

Comandos determinísticos equivalentes:

```bash
tide taiga create-from-wave TIDE-0005 --yes
tide taiga sync TIDE-0005 --yes
```

## Sem `/approve --taiga`

Não existe design de `/approve --taiga`.

`/approve` continua responsável apenas por aprovação/commit local.

Se a Wave já estiver vinculada ao Taiga, o Tide pode chamar `tide-taiga` depois do commit como evento natural de sincronização. Se Taiga falhar, o commit não é revertido.

## Configuração

Configure com:

```bash
tide taiga configure
```

O comando pede:

- base URL da API;
- project ID;
- default kind: `task`, `userstory` ou `issue`;
- token de acesso.

Exemplo não sensível:

```bash
tide taiga configure \
  --base-url=https://taiga.example/api/v1 \
  --project-id=43
```

O token é pedido de forma interativa quando `--token` não é informado.

Diagnóstico:

```bash
tide taiga doctor
tide taiga show
tide taiga whoami
```

Remoção:

```bash
tide taiga logout
```

## Comandos disponíveis

Read-only:

```bash
tide taiga whoami
tide taiga projects
tide taiga statuses --kind task
tide taiga members
tide taiga list --kind task
tide taiga get --kind task --ref 231
tide taiga maturity --kind task --ref 231
```

Escrita no Taiga, sempre com `--yes`:

```bash
tide taiga create --kind task --subject "Título" --description "Descrição" --yes
tide taiga comment --kind task --ref 231 --text "Comentário" --yes
tide taiga update --kind task --ref 231 --status "Em andamento" --yes
tide taiga sync TIDE-0005 --yes
tide taiga create-from-wave TIDE-0005 --kind task --yes
```

Para texto longo, use stdin em vez de wrapper/script intermediário:

```bash
tide taiga create \
  --kind task \
  --subject "Título" \
  --description-stdin \
  --yes <<'EOF'
Descrição longa em múltiplas linhas.
EOF


tide taiga comment \
  --kind task \
  --ref 231 \
  --text-stdin \
  --yes <<'EOF'
Comentário longo em múltiplas linhas.
EOF


tide taiga update \
  --kind task \
  --ref 231 \
  --description-stdin \
  --yes <<'EOF'
Nova descrição longa.
EOF
```

Metadado local de Wave, sem escrever no Taiga:

```bash
tide taiga link TIDE-0005 --kind task --ref 231
```

## Armazenamento

Config não sensível:

```txt
~/.config/tide/taiga/config.json
```

Token:

- macOS: Keychain via comando `security`;
- fallback explícito: arquivo local `~/.config/tide/taiga/token` com `chmod 600`, apenas com `--allow-local-token`.

Não use `.env` por projeto para credenciais Taiga.

## Metadados locais da Wave

O vínculo recomendado fica em `.opencode/waves/<id>/wave.json`:

```json
{
  "taiga": {
    "enabled": true,
    "ref": 231,
    "kind": "task",
    "project_id": 43,
    "auto_sync": true,
    "created_by_tide": false,
    "last_sync": null
  }
}
```

Esses metadados não são credenciais.

## Automação segura

Com Taiga ativo:

- comentários de progresso/fechamento podem ser automáticos;
- criação inicial, edição substancial, status, assignee e sprint exigem confirmação explícita;
- falha no Taiga não desfaz commit nem estado local;
- nenhuma credencial deve aparecer no output.

## Componentes

```txt
bin/tide-taiga
opencode/agents/tide-taiga.md
opencode/skills/taiga/SKILL.md
tide taiga configure|doctor|whoami|get|create|comment|update|link|sync|create-from-wave
```
