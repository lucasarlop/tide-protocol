# Taiga Safety Constraints

A integração Taiga do Tide deve usar apenas comandos já definidos do protocolo.

O agente `tide-taiga` deve operar com o comando `tide taiga`. Ele não deve criar arquivo auxiliar, automação local ou implementação nova dentro do projeto para falar com o Taiga. Se faltar um comando, o agente deve parar e reportar a limitação como melhoria do protocolo.

Comandos de leitura permitidos: doctor, show, whoami, projects, statuses, members, list, get e maturity.

Comandos de escrita permitidos: create, comment, update, sync e create-from-wave. Todos exigem confirmação explícita e a opção `--yes`.

Vínculo local permitido: link. Esse comando registra metadado local da Wave e não escreve no Taiga.

Operações de remoção no Taiga não fazem parte do fluxo do agente. Se o supervisor precisar remover algo, trate como ação manual fora da automação Taiga.

`logout` é manutenção manual do usuário. O agente não deve chamar esse comando como parte de uma Wave.

Quando faltar comando, a resposta correta é informar que a operação ainda não existe no Tide e sugerir uma Wave de evolução do protocolo. Não improvise integração local.
