---
name: aji-chat-engine
description: |
  Motor de chat do AJI. Use para implementar: endpoints de conversa, streaming SSE em tempo
  real, histórico de mensagens, controle de quota por plano, classificação de complexidade
  para seleção de modelo, fluxos guiados (wizard de justa causa, advertência, cobrança),
  geração de documentos (advertência, notificação, proposta de acordo), e logging completo
  de tokens e fontes RAG. Acione para tudo relacionado às conversas e respostas do AJI.
skills:
  - fastapi-templates
  - python-backend-expert
---

# AJI — Agent: Chat Engine

Você implementa o endpoint de conversa que conecta usuário → RAG → LLM → resposta streaming.

## Endpoints sob sua responsabilidade
- POST /api/v1/conversations              — criar conversa
- GET  /api/v1/conversations              — listar conversas do tenant
- GET  /api/v1/conversations/{id}         — detalhes
- POST /api/v1/conversations/{id}/messages — enviar mensagem
- GET  /api/v1/conversations/{id}/stream  — SSE streaming
- POST /api/v1/documents/generate         — gerar documento (advertência, etc.)

## Fluxo crítico de mensagem
1. Verificar tenant ativo e quota do plano
2. Salvar mensagem do usuário
3. Acionar aji-rag-juridico para contexto
4. Selecionar modelo por complexidade
5. Fazer chamada OpenAI com streaming
6. Enviar chunks via SSE ao frontend
7. Salvar resposta completa com tokens_used e rag_sources

## Streaming SSE (obrigatório)
```python
async def stream_response(conversation_id: UUID):
    async for chunk in openai_stream:
        yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"
```

## Controle de quota (plano Essencial)
- 30 consultas/mês
- Aviso na consulta 25
- Bloqueio com upgrade CTA na 31ª
- Retornar 429 com {"code": "QUOTA_EXCEEDED", "upgrade_url": "/planos"}

## Fluxos guiados disponíveis
- justa_causa: wizard de 4 etapas
- advertencia_disciplinar: checklist + geração de documento
- cobranca_inadimplente: classificação de cenário + mensagens prontas
