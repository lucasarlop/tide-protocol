# Código Vivo

O Tide trata o código atual como fonte da verdade.

A camada de Código Vivo serve para acelerar contexto, não para substituir leitura, testes ou revisão do estado real do projeto.

## Fonte da verdade

Sempre considere, nesta ordem:

1. código atual;
2. `git status`;
3. diff atual;
4. validações executadas;
5. contexto indexado, quando disponível.

## code-review-graph

`code-review-graph` é integração recomendada, mas opcional.

Quando disponível, o agente pode usar o grafo para:

- localizar símbolos relevantes;
- entender impacto provável;
- reduzir leitura desnecessária;
- montar contexto para review.

Quando não estiver disponível, o Tide deve seguir usando leitura direta do projeto.

## Regra de segurança

Contexto indexado pode estar atrasado. Antes de implementar ou aprovar uma Wave, valide contra o código atual.

## Próxima evolução

A integração runtime completa deve expor comandos como:

```txt
tide context status
tide context update
tide context query <termo>
```

Esses comandos devem funcionar com fallback quando não houver grafo.
