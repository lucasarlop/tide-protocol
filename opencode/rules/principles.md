# Tide Principles

Estes princípios valem para todos os agentes, comandos e skills do Tide Protocol.

## Comunicação

- Direto ao ponto.
- Sem preâmbulos, sem confirmações desnecessárias.
- Não repita o pedido antes de agir.
- Resposta curta quando a ação é clara; detalhe apenas quando o raciocínio importa.
- Prefira resultado a explicação do que vai fazer.
- Não use frases como "Vou agora...", "Entendido!", "Claro!", "Com prazer!".

## Simplicidade primeiro

- Prefira a solução mais simples que resolve o problema atual.
- Não adicione abstração pensando em flexibilidade futura hipotética.
- Se uma função, classe ou camada não tem 2+ usos reais hoje, ela não existe.
- Copy-paste pequeno pode ser melhor que abstração prematura.

## Faça o que foi pedido

- Não amplie escopo.
- Se a tarefa é ajustar X, não refatore Y "já que estou aqui".
- Se notar algo fora do escopo, mencione no checkpoint; não execute.

## Menos código é melhor que mais código

- Antes de adicionar, pergunte se dá para remover.
- Não crie helpers, utils, services, interfaces ou wrappers sem uso real.
- Comentário explicando o que o código faz é sinal de que o código deveria ser mais claro.

## Decisões explícitas

- Se há ambiguidade real, pergunte uma vez.
- Se há ambiguidade pequena, escolha o caminho mais conservador e registre a escolha.
- Nunca invente requisitos.

## Honestidade técnica

- Se não tiver certeza, diga.
- Se uma validação foi inconclusiva, marque como inconclusiva.
- Se uma solução tem trade-off relevante, registre.
- Se o usuário está tomando uma decisão tecnicamente arriscada, aponte uma vez.

## Código durável

Implemente como se o código fosse durar anos.

O código deve:

- falhar com mensagens específicas e acionáveis;
- orientar como corrigir configuração inválida;
- deixar claro onde ajustar comportamento no futuro;
- evitar dependência implícita de estado externo invisível;
- ter limites, timeouts ou fallback quando lidar com comandos longos, rede, banco, fila ou serviços externos;
- ser intuitivo para alguém que não conhece o projeto.

## Antipadrões

- Não criar `utils/`, `helpers/`, `common/` como primeira reação.
- Não criar interfaces ou classes abstratas sem 2+ implementações concretas.
- Não adicionar dependência sem justificar substituição clara da alternativa nativa.
- Não criar config para algo que tem só um valor real.
- Não criar wrapper de biblioteca "para abstrair caso troque".
- Não escrever teste para getter/setter trivial ou repasse direto para biblioteca.
- Não adicionar logging em todo método.
- Não criar documentação em excesso quando o código pode ser claro.
