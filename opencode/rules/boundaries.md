# Fronteiras

O Tide é Boundary-First. O processo nasce do risco e das fronteiras, não de um pipeline fixo.

## Fronteiras sensíveis
Acione checkpoint prévio ou reviewer especializado quando houver:

- banco, migration, query destrutiva ou reprocessamento de dados;
- auth, billing, permissões, tokens, secrets ou input externo;
- SSH, produção, deploy, CI/CD, infra ou workers;
- nova dependência;
- alteração de contrato público/API;
- muitos arquivos ou múltiplos módulos;
- comando lento, travado, desconhecido ou com side effect real.

## Regra principal
Dentro da fronteira: aja.

Para cruzar a fronteira: pare.

## Change budget
Toda Wave de código deve declarar budget proporcional:

- arquivos máximos;
- paths permitidos;
- paths proibidos;
- dependências permitidas;
- comandos permitidos;
- critérios para parar.
