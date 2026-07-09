# Taiga Safety Rule

A integração Taiga do Tide deve usar apenas comandos já definidos do protocolo.

Agentes não devem criar código, arquivos auxiliares, automações locais ou implementações novas dentro do projeto para falar com o Taiga. O caminho correto é usar o comando `tide taiga`.

Se faltar um comando para uma operação, o agente deve parar e reportar a limitação como melhoria do protocolo. Não improvise integração local.

Também não é permitido importar o helper `tide-taiga` em Python, ler token/configuração diretamente, ou contornar bug do CLI em memória. Se o CLI falhar, reporte o erro e sugira atualização do Tide.

Antes de qualquer escrita real no Taiga, o agente deve imprimir o que pretende alterar e aguardar autorização ou ajuste do supervisor.

Fluxo obrigatório para escrita no Taiga:

1. executar o comando com `--dry-run`;
2. mostrar o plano ao supervisor;
3. aguardar aprovação explícita ou ajustes;
4. executar o mesmo comando com `--yes` e sem `--dry-run` somente após aprovação.

Operações de leitura permitidas pelo fluxo Taiga: doctor, show, whoami, projects, statuses, members, list, find, get e maturity.

Operações de escrita permitidas pelo fluxo Taiga: create, comment, update, sync e create-from-wave. Todas exigem preview prévio, confirmação explícita e a opção `--yes`.

Vínculo local permitido: link. Esse comando registra metadado local da Wave e não escreve no Taiga.

Operações de remoção no Taiga não fazem parte do fluxo do agente. Se o supervisor precisar remover algo, trate como ação manual fora da automação Taiga.

`logout` é manutenção manual do usuário. O agente não deve chamar esse comando como parte de uma Wave.
