---
name: tide-durable-code
description: Implementar e revisar código durável: falhas claras, configuração acionável e manutenção intuitiva.
license: MIT
compatibility: opencode
---

# tide-durable-code

Código durável deve:
- falhar bem;
- orientar bem;
- operar bem;
- deixar claro onde ajustar.

## Checklist
- Env/config inválida tem mensagem específica?
- A mensagem diz como corrigir?
- Falhas externas têm limite, timeout, fallback ou erro explícito?
- Alguém novo saberia onde procurar?
- O caminho de falha é compreensível?
- A solução segue padrões existentes?
- A mudança evita abstração prematura?
