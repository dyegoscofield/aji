"""
Chat engine do AJI — integração OpenAI com streaming SSE e RAG.

Responsabilidades:
- Monta o contexto da conversa (histórico + RAG)
- Seleciona o modelo adequado (gpt-4o-mini ou gpt-4o)
- Gera streaming SSE da resposta
- O sistema prompt já inclui o disclaimer obrigatório — NUNCA remover

Regras de segurança:
- OPENAI_API_KEY inválida → yield SSE de erro (sem exception para não quebrar o stream)
- Histórico limitado a 10 mensagens para controle de tokens
- Contexto RAG injetado apenas quando não-vazio
"""

import json
import logging
import uuid
from typing import AsyncGenerator

from openai import AsyncOpenAI, AuthenticationError, APIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.message import Message

logger = logging.getLogger(__name__)

# Limite de histórico de mensagens enviadas ao LLM — controle de custo de tokens
HISTORY_LIMIT = 10

# Disclaimer obrigatório incluso no system prompt (CLAUDE.md seção 15 e 10)
SYSTEM_PROMPT = """Você é o AJI — Assistente Jurídico Inteligente, especializado em orientação jurídica preventiva para empresários brasileiros.

Estruture SEMPRE suas respostas assim:
1. **Situação** — o que está acontecendo juridicamente
2. **Orientação** — o que geralmente se faz / como funciona na prática
3. **Riscos** — o que pode dar errado se agir incorretamente
4. **Próximo passo** — ação concreta + quando escalar ao advogado

Regras obrigatórias:
- Cite a base legal quando relevante (ex: "conforme art. 482 da CLT")
- NUNCA garanta resultados ou outcomes jurídicos
- NUNCA use os termos: "consultoria jurídica", "assessoria jurídica", "substitui o advogado"
- Use linguagem clara, sem juridiquês excessivo
- Sempre inclua o disclaimer ao final

Disclaimer obrigatório (incluir em TODA resposta):
---
⚠️ *Esta orientação é informativa e não substitui a análise de um advogado. Para situações de risco judicial ou que exijam representação legal, consulte um profissional habilitado pela OAB.*
"""

_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def _get_recent_history(
    conversation_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
    limit: int = HISTORY_LIMIT,
) -> list[dict[str, str]]:
    """
    Busca o histórico recente da conversa para contexto do LLM.

    Regra de multi-tenancy: filtra obrigatoriamente por tenant_id,
    mesmo que conversation_id já identifique a conversa de forma única.

    Retorna as últimas `limit` mensagens ordenadas por created_at crescente,
    no formato de mensagens para a API da OpenAI.

    Args:
        conversation_id: UUID da conversa.
        tenant_id:       UUID do tenant (OBRIGATÓRIO — multi-tenancy).
        db:              Sessão assíncrona.
        limit:           Máximo de mensagens a retornar.

    Returns:
        Lista de dicts {"role": "user"|"assistant", "content": str}.
    """
    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant_id,   # OBRIGATÓRIO — multi-tenancy
            Message.role.in_(["user", "assistant"]),
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    # Inverter para ordem cronológica (mais antigo → mais recente)
    return [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(messages)
    ]


def _build_user_message(query: str, rag_context: str) -> str:
    """
    Monta o conteúdo da mensagem do usuário com contexto RAG injetado.

    O contexto RAG é injetado apenas quando não-vazio para não poluir
    o prompt com seção vazia.

    Args:
        query:       Pergunta original do usuário.
        rag_context: Contexto jurídico montado pelo retrieval (pode ser vazio).

    Returns:
        String formatada para o campo "content" da mensagem do usuário.
    """
    if rag_context:
        return (
            f"Contexto jurídico relevante:\n{rag_context}\n\n"
            f"Pergunta: {query}"
        )
    return query


async def stream_chat_response(
    query: str,
    conversation_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
    model: str = "gpt-4o-mini",
    rag_context: str = "",
) -> AsyncGenerator[str, None]:
    """
    Gera streaming SSE da resposta do OpenAI com contexto RAG.

    Protocolo SSE:
    - Chunks de texto: `data: {"text": "<conteúdo>"}\n\n`
    - Evento de conclusão: `data: {"done": true, "model": "<model>", "tokens": <int>}\n\n`
    - Evento de erro: `data: {"error": "<mensagem>"}\n\n`

    O erro de API key inválida é tratado sem levantar exception para não quebrar
    o stream HTTP — o cliente recebe um evento de erro estruturado.

    Args:
        query:           Pergunta do usuário.
        conversation_id: UUID da conversa atual.
        tenant_id:       UUID do tenant (para buscar histórico com isolamento).
        db:              Sessão assíncrona do banco de dados.
        model:           Modelo OpenAI selecionado.
        rag_context:     Contexto jurídico montado pelo retrieval.

    Yields:
        Strings no formato SSE.
    """
    # 1. Buscar histórico recente (sem a mensagem atual — já foi salva antes)
    history = await _get_recent_history(
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        db=db,
        limit=HISTORY_LIMIT,
    )

    # 2. Montar array de mensagens para a API
    # O histórico já inclui a mensagem do usuário que acabou de ser salva.
    # Removemos o último item do histórico (user) e adicionamos com RAG injetado.
    if history and history[-1]["role"] == "user":
        history = history[:-1]

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": _build_user_message(query, rag_context)},
    ]

    # 3. Chamar OpenAI com streaming
    client = _get_openai_client()

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            stream=True,
            temperature=0.3,    # Baixa temperatura para respostas jurídicas consistentes
            max_tokens=2000,
        )

        total_tokens = 0

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                text = delta.content
                yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"

            # Capturar usage do último chunk (quando stream_options inclui usage)
            if chunk.usage:
                total_tokens = chunk.usage.total_tokens

        # 4. Evento de conclusão
        yield f"data: {json.dumps({'done': True, 'model': model, 'tokens': total_tokens})}\n\n"

    except AuthenticationError:
        logger.error(
            "OPENAI_API_KEY inválida ao tentar stream de chat. "
            "Verifique a configuração da variável de ambiente."
        )
        yield (
            f"data: {json.dumps({'error': 'Serviço de IA temporariamente indisponível'})}\n\n"
        )

    except APIError as exc:
        logger.error("Erro de API OpenAI no stream de chat: %s", exc)
        yield (
            f"data: {json.dumps({'error': 'Serviço de IA temporariamente indisponível'})}\n\n"
        )
