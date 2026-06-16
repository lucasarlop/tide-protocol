# Durability Gate

Antes de considerar uma Wave relevante como pronta, verifique:

- Env/config ausente ou inválida gera erro claro?
- A mensagem explica como corrigir?
- Falhas externas são tratadas com limite, timeout, fallback ou erro específico?
- A rotina continua intuitiva para alguém novo no projeto?
- Está claro onde ajustar comportamento no futuro?
- O caminho de falha é tão compreensível quanto o caminho feliz?
- A mudança segue padrões atuais do sistema?
- A solução evita abstração prematura?

Se a resposta relevante for não, a Wave não está pronta ou deve registrar risco no checkpoint.
