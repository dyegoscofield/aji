# Padrões de API e Testes

## Convenções de Código

```python
# Sempre usar:
# - Type hints em tudo
# - Pydantic v2 para schemas
# - SQLAlchemy 2.0 style (async)
# - Dependency injection via FastAPI Depends()
# - Nunca retornar objetos ORM diretamente — sempre serializar com schema
```

## Endpoint de Chat (Core do Produto)

```python
# app/api/v1/chat.py

@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    body: MessageCreateSchema,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    aji_service: AJIService = Depends(get_aji_service),
):
    # Verificar limites do plano
    if tenant.plan == "essencial":
        monthly_count = await MessageRepository.count_this_month(db, tenant.id)
        if monthly_count >= 30:
            raise HTTPException(429, detail={
                "code": "QUOTA_EXCEEDED",
                "message": "Limite de 30 consultas mensais atingido.",
                "upgrade_url": "/planos"
            })
    
    # Verificar conversa pertence ao tenant (MULTI-TENANCY OBRIGATÓRIO)
    conversation = await ConversationRepository.get(db, conversation_id)
    if conversation.tenant_id != tenant.id:
        raise HTTPException(403, "Acesso negado")
    
    # Salvar mensagem do usuário
    user_msg = await MessageRepository.create(db, {
        "conversation_id": conversation_id,
        "role": "user",
        "content": body.content,
    })
    
    # Chamar pipeline AJI (RAG + GPT-4o)
    response = await aji_service.process(
        query=body.content,
        tenant=tenant,
        conversation_history=await MessageRepository.get_history(db, conversation_id),
    )
    
    # Salvar resposta
    ai_msg = await MessageRepository.create(db, {
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": response.content,
        "tokens_used": response.tokens,
        "model": response.model,
        "rag_sources": response.sources,
    })
    
    return MessageResponseSchema.from_orm(ai_msg)
```

## Padrões de Resposta de Erro

```python
# Sempre retornar erros estruturados:
{
    "code": "QUOTA_EXCEEDED",      # Código interno
    "message": "...",              # Mensagem para o usuário
    "details": {...},              # Info adicional (opcional)
    "upgrade_url": "/planos"       # Ação sugerida (opcional)
}
```

## Testes Obrigatórios

```python
# Sempre criar testes para:
# 1. Happy path
# 2. CNPJ inválido / empresa inativa
# 3. Tenant não encontrado / acesso negado (multi-tenancy)
# 4. Quota excedida
# 5. Stripe webhook com assinatura inválida

@pytest.mark.asyncio
async def test_send_message_quota_exceeded(client, essencial_tenant):
    # Simular 30 mensagens este mês
    await seed_messages(essencial_tenant.id, count=30)
    
    response = await client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"content": "teste"},
        headers={"Authorization": f"Bearer {essencial_tenant.token}"}
    )
    
    assert response.status_code == 429
    assert response.json()["code"] == "QUOTA_EXCEEDED"
```
