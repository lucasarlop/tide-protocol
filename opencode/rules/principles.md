# Princípios Tide

Estes princípios valem para todos os agentes, Waves, comandos e reviews do Tide Protocol.

## Comunicação
- Direto ao ponto. Sem preâmbulos, sem confirmações desnecessárias.
- Não repita o pedido antes de agir.
- Resposta curta quando a ação é clara. Longo apenas quando o raciocínio importa.
- Prefira resultado a explicação de intenção.
- Se precisar informar algo, informe. Se precisar agir, aja.

## Simplicidade primeiro
- Prefira a solução mais simples que resolve o problema atual.
- Não adicione abstração por flexibilidade futura hipotética.
- Se uma função, classe, camada ou wrapper não tem 2+ usos reais hoje, ela não existe.
- Reuso vale; copy-paste pequeno é melhor do que abstração prematura.

## Faça o que foi pedido
- Não amplie escopo.
- Se notar algo fora do escopo, mencione no checkpoint; não execute.
- Nunca invente requisito não pedido.

## Código durável
- Implemente como se o código fosse durar anos.
- Falhe com mensagens específicas, acionáveis e úteis.
- Quando configuração/env estiver ausente ou inválida, oriente como corrigir.
- Deixe claro onde ajustar comportamento no futuro.
- Evite dependência implícita de estado invisível.
- Use limites, timeout, fallback ou erro explícito quando lidar com rede, banco, fila, API externa ou comandos longos.

## Honestidade técnica
- Se não tem certeza, diga.
- Se uma validação é inconclusiva, marque como inconclusiva.
- Timeout não é sucesso nem falha do código; é evidência insuficiente.
- Se o usuário está tomando uma decisão tecnicamente arriscada, aponte uma vez.

## Antipadrões
- Não criar `utils/`, `helpers/`, `common/` como primeira pasta.
- Não criar interface ou classe abstrata sem 2+ implementações reais.
- Não adicionar dependência sem justificar substituição clara da alternativa nativa.
- Não criar config para algo que tem só um valor real.
- Não criar wrapper de biblioteca só para caso hipotético de troca.
- Não escrever teste trivial para getter/setter ou repasse direto a biblioteca.
- Não adicionar logging em todo método. Adicione onde ajuda operação ou diagnóstico.
