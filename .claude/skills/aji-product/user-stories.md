# User Stories Principais do AJI

## US-01: Empresário faz primeira consulta

```
Como empresário com dúvida trabalhista
Quero consultar o AJI sobre o procedimento correto
Para tomar uma decisão com mais segurança

Critérios de aceitação:
- [ ] Posso fazer minha pergunta em linguagem natural
- [ ] Recebo resposta em menos de 10 segundos
- [ ] A resposta cita a base legal relevante
- [ ] A resposta indica se devo consultar advogado
- [ ] Posso continuar a conversa com perguntas de follow-up
```

## US-02: Contador indica para cliente

```
Como contador parceiro
Quero compartilhar meu link de indicação com um cliente
Para que ele se cadastre e eu receba comissão

Critérios de aceitação:
- [ ] Recebo um link único de indicação no cadastro
- [ ] Posso ver quantos clientes se cadastraram pelo meu link
- [ ] Recebo confirmação por email quando cliente converte
- [ ] Minha comissão é calculada automaticamente
```

## US-03: Limite de uso — plano Essencial

```
Como sistema
Quando um usuário do plano Essencial atingir 30 consultas no mês
Devo notificá-lo e oferecer upgrade

Critérios de aceitação:
- [ ] Aviso na consulta 25 (5 restantes)
- [ ] Bloqueio com mensagem clara na consulta 31
- [ ] CTA para upgrade inline
- [ ] Contagem reinicia no dia 1 de cada mês
```

## Template para Novas User Stories

```markdown
## US-XX: [Título descritivo]

Como [persona]
Quero [ação]
Para [benefício]

Critérios de aceitação:
- [ ] [Critério verificável]
- [ ] [Critério verificável]

Notas técnicas:
- [Dependências, impactos, riscos]

Compliance:
- [ ] Verificado com aji-legal? (obrigatório se envolve orientação jurídica)
```
