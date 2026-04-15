"""
Endpoints de chat e RAG do AJI.

GET  /api/v1/chat/search                                  — Busca semântica (debug/validação)
POST /api/v1/chat/conversations                           — Criar nova conversa
GET  /api/v1/chat/conversations                           — Listar conversas do tenant
POST /api/v1/chat/conversations/{id}/messages             — Enviar mensagem (SSE streaming)
GET  /api/v1/chat/conversations/{id}/messages             — Histórico de mensagens

Regras críticas:
- TODA query ao banco DEVE incluir tenant_id (multi-tenancy)
- Quota verificada ANTES de processar a mensagem
- Ownership da conversa verificado antes de aceitar mensagem
- StreamingResponse com persistência da mensagem do assistente após o stream
"""

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_tenant, get_current_user
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai.chat_service import stream_chat_response
from app.services.ai.model_selector import select_model
from app.services.ai.quota import check_quota
from app.services.rag.retrieval import assemble_context, search_similar_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Schemas Pydantic v2
# ---------------------------------------------------------------------------


class ConversationCreateSchema(BaseModel):
    channel: str = Field(default="web", pattern="^(web|whatsapp)$")


class ConversationResponseSchema(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    channel: str
    status: str
    topic: str | None

    model_config = {"from_attributes": True}


class MessageCreateSchema(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponseSchema(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    content: str
    tokens_used: int | None
    model: str | None
    rag_sources: dict | None

    model_config = {"from_attributes": True}


class ConversationListResponseSchema(BaseModel):
    total: int
    items: list[ConversationResponseSchema]


# ---------------------------------------------------------------------------
# Helper: salvar mensagem do assistente após stream
# ---------------------------------------------------------------------------


async def _save_assistant_message(
    conversation_id: uuid.UUID,
    tenant_id: uuid.UUID,
    content: str,
    tokens_used: int,
    model: str,
    rag_sources: dict,
    db: AsyncSession,
) -> None:
    """
    Persiste a mensagem do assistente no banco após o stream ser completado.

    Usa uma nova sessão implícita via commit — o db passado já é o da request.
    Multi-tenancy: tenant_id desnormalizado na mensagem.
    """
    assistant_msg = Message(
        conversation_id=conversation_id,
        tenant_id=tenant_id,   # desnormalizado — OBRIGATÓRIO
        role="assistant",
        content=content,
        tokens_used=tokens_used if tokens_used > 0 else None,
        model=model,
        rag_sources=rag_sources if rag_sources.get("chunks") else None,
    )
    db.add(assistant_msg)
    await db.commit()


# ---------------------------------------------------------------------------
# Gerador SSE com persistência
# ---------------------------------------------------------------------------


async def _message_stream_generator(
    query: str,
    conversation_id: uuid.UUID,
    tenant_id: uuid.UUID,
    model: str,
    rag_context: str,
    rag_chunks: list[dict],
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Gera o stream SSE e, ao final, persiste a mensagem do assistente no banco.

    O texto completo é acumulado em memória para persistência —
    respostas jurídicas são tipicamente 300–800 palavras, sem risco de OOM.
    """
    text_parts: list[str] = []
    tokens_used: int = 0
    final_model: str = model
    had_error: bool = False

    async for chunk in stream_chat_response(
        query=query,
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        db=db,
        model=model,
        rag_context=rag_context,
    ):
        yield chunk

        # Parsear chunk SSE para acumular texto e metadados
        if chunk.startswith("data: "):
            raw = chunk[len("data: "):].strip()
            try:
                data = json.loads(raw)
                if "text" in data:
                    text_parts.append(data["text"])
                elif "done" in data and data["done"]:
                    tokens_used = data.get("tokens", 0)
                    final_model = data.get("model", model)
                elif "error" in data:
                    had_error = True
            except (json.JSONDecodeError, KeyError):
                pass

    # Persistir mensagem do assistente apenas se o stream não teve erro
    if not had_error and text_parts:
        full_content = "".join(text_parts)
        rag_sources_data = {
            "chunks": [
                {
                    "id": c.get("id"),
                    "source_file": c.get("source_file"),
                    "score": c.get("score"),
                }
                for c in rag_chunks
            ]
        }
        try:
            await _save_assistant_message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                content=full_content,
                tokens_used=tokens_used,
                model=final_model,
                rag_sources=rag_sources_data,
                db=db,
            )
        except Exception as exc:
            # Log mas não interrompe — o cliente já recebeu a resposta completa
            logger.error(
                "Falha ao persistir mensagem do assistente "
                "(conversation_id=%s, tenant_id=%s): %s",
                conversation_id,
                tenant_id,
                exc,
            )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/search")
async def search_rag(
    q: str = Query(..., min_length=3, max_length=1000, description="Consulta jurídica"),
    top_k: int = Query(default=5, ge=1, le=20, description="Número de chunks a retornar"),
    min_score: float = Query(
        default=0.7, ge=0.0, le=1.0, description="Score mínimo de similaridade"
    ),
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca semântica na base jurídica do RAG.

    Endpoint de debug e validação — útil para verificar a qualidade do retrieval
    antes de integrar ao chat engine. Requer autenticação.

    Retorna os chunks mais relevantes com score de similaridade.
    Multi-tenancy: retorna apenas chunks globais e do tenant autenticado.
    """
    tenant_id: uuid.UUID = current_tenant.id

    try:
        chunks = await search_similar_chunks(
            query=q,
            db=db,
            tenant_id=tenant_id,
            top_k=top_k,
            min_score=min_score,
        )
    except RuntimeError as exc:
        logger.error(
            "Falha no embedding para busca RAG (tenant_id=%s): %s",
            tenant_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Serviço de busca temporariamente indisponível. "
                "Tente novamente em alguns instantes."
            ),
        )

    context = assemble_context(chunks) if chunks else ""

    return {
        "query": q,
        "tenant_id": str(tenant_id),
        "total_results": len(chunks),
        "chunks": chunks,
        "context_assembled": context,
        "params": {
            "top_k": top_k,
            "min_score": min_score,
        },
    }


@router.post(
    "/conversations",
    response_model=ConversationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    body: ConversationCreateSchema = ConversationCreateSchema(),
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria uma nova conversa para o tenant autenticado.

    Multi-tenancy: tenant_id extraído do token JWT — nunca do body.
    """
    conversation = Conversation(
        tenant_id=current_tenant.id,   # OBRIGATÓRIO — do token, nunca do body
        user_id=current_user.id,
        channel=body.channel,
        status="active",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    logger.info(
        "Conversa criada: id=%s tenant_id=%s user_id=%s channel=%s",
        conversation.id,
        conversation.tenant_id,
        conversation.user_id,
        conversation.channel,
    )

    return ConversationResponseSchema.model_validate(conversation)


@router.get(
    "/conversations",
    response_model=ConversationListResponseSchema,
)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista conversas do tenant autenticado (paginado).

    Multi-tenancy: filtra SEMPRE por tenant_id do token JWT.
    Retorna apenas conversas do tenant — nunca de outros tenants.
    """
    tenant_id = current_tenant.id

    # Contar total
    count_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == tenant_id,  # OBRIGATÓRIO — multi-tenancy
        )
    )
    total = count_result.scalar_one()

    # Buscar página
    items_result = await db.execute(
        select(Conversation)
        .where(
            Conversation.tenant_id == tenant_id,  # OBRIGATÓRIO — multi-tenancy
        )
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    conversations = items_result.scalars().all()

    return ConversationListResponseSchema(
        total=total,
        items=[ConversationResponseSchema.model_validate(c) for c in conversations],
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    status_code=status.HTTP_200_OK,
)
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageCreateSchema,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Envia mensagem e retorna StreamingResponse (SSE).

    Fluxo:
    1. check_quota — verifica trial e limite mensal ANTES de processar
    2. Verifica ownership da conversa (tenant_id do token == conversation.tenant_id)
    3. Salva mensagem do usuário
    4. RAG: busca chunks relevantes
    5. Seleciona modelo por complexidade
    6. Inicia stream SSE
    7. Ao final do stream: persiste mensagem do assistente

    Multi-tenancy: toda query filtra por tenant_id. Ownership verificado antes de processar.

    SSE Events:
        data: {"text": "..."}\n\n       — chunk de texto
        data: {"done": true, ...}\n\n   — stream concluído
        data: {"error": "..."}\n\n      — erro (API key inválida, etc.)
    """
    # 1. Verificar quota (trial expirado → 402, limite atingido → 429)
    await check_quota(tenant=current_tenant, db=db)

    # 2. Verificar ownership da conversa — MULTI-TENANCY CRÍTICO
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == current_tenant.id,  # OBRIGATÓRIO
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCESS_DENIED",
                "message": "Conversa não encontrada ou acesso negado.",
            },
        )

    if conversation.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CONVERSATION_CLOSED",
                "message": "Esta conversa está encerrada. Crie uma nova conversa.",
            },
        )

    # 3. Salvar mensagem do usuário
    user_message = Message(
        conversation_id=conversation_id,
        tenant_id=current_tenant.id,   # desnormalizado — OBRIGATÓRIO
        role="user",
        content=body.content,
    )
    db.add(user_message)
    await db.commit()

    # 4. RAG: buscar chunks relevantes
    rag_chunks: list[dict] = []
    rag_context = ""
    try:
        rag_chunks = await search_similar_chunks(
            query=body.content,
            db=db,
            tenant_id=current_tenant.id,
            top_k=5,
            min_score=0.7,
        )
        if rag_chunks:
            rag_context = assemble_context(rag_chunks)
    except RuntimeError as exc:
        # Falha de embedding não impede o chat — continua sem contexto RAG
        logger.warning(
            "Falha no RAG para conversation_id=%s tenant_id=%s: %s. "
            "Continuando sem contexto RAG.",
            conversation_id,
            current_tenant.id,
            exc,
        )

    # 5. Selecionar modelo por complexidade da query
    model = select_model(body.content)

    logger.info(
        "Iniciando stream: conversation_id=%s tenant_id=%s model=%s rag_chunks=%d",
        conversation_id,
        current_tenant.id,
        model,
        len(rag_chunks),
    )

    # 6 + 7. Stream SSE com persistência ao final
    return StreamingResponse(
        content=_message_stream_generator(
            query=body.content,
            conversation_id=conversation_id,
            tenant_id=current_tenant.id,
            model=model,
            rag_context=rag_context,
            rag_chunks=rag_chunks,
            db=db,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Nginx: desabilitar buffer para SSE
        },
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponseSchema],
)
async def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna o histórico de mensagens de uma conversa.

    Multi-tenancy: verifica ownership da conversa pelo tenant_id do token JWT.
    Retorna 403 se a conversa pertencer a outro tenant.
    """
    # Verificar ownership — MULTI-TENANCY CRÍTICO
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == current_tenant.id,  # OBRIGATÓRIO
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCESS_DENIED",
                "message": "Conversa não encontrada ou acesso negado.",
            },
        )

    # Buscar mensagens — filtrar por AMBOS conversation_id e tenant_id
    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == current_tenant.id,  # OBRIGATÓRIO — multi-tenancy
        )
        .order_by(Message.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()

    return [MessageResponseSchema.model_validate(m) for m in messages]
