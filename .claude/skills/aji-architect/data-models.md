# Modelos de Dados Principais do AJI

## Tenants (empresas)

```python
class Tenant(Base):
    id: UUID
    cnpj: str (unique, indexed)
    razao_social: str
    plan: Enum['essencial', 'profissional', 'personalizado']
    status: Enum['trial', 'active', 'suspended', 'cancelled']
    stripe_customer_id: str
    stripe_subscription_id: str
    partner_id: UUID (FK, nullable)
    created_at: datetime
    trial_ends_at: datetime
    knowledge_base_id: UUID (FK, nullable)  # Para plano personalizado
```

## Users

```python
class User(Base):
    id: UUID
    tenant_id: UUID (FK)
    email: str
    role: Enum['owner', 'admin', 'member']
    is_active: bool
    last_login: datetime
```

## Conversations

```python
class Conversation(Base):
    id: UUID
    tenant_id: UUID (FK)
    user_id: UUID (FK)
    channel: Enum['web', 'whatsapp']
    status: Enum['active', 'escalated', 'closed']
    topic: str (nullable, extracted by AI)
    created_at: datetime
```

## Messages

```python
class Message(Base):
    id: UUID
    conversation_id: UUID (FK)
    role: Enum['user', 'assistant', 'system']
    content: str
    tokens_used: int
    model: str
    rag_sources: JSONB  # documentos usados na resposta
    created_at: datetime
```

## Partners (contadores)

```python
class Partner(Base):
    id: UUID
    name: str
    email: str
    cnpj: str
    referral_code: str (unique)
    commission_rate: Decimal (default 0.20)
    status: Enum['pending', 'active', 'suspended']
    bank_data: JSONB (encrypted)
    total_referrals: int
    active_referrals: int
```

## Regras de Integridade

1. **Multi-tenancy:** Toda query DEVE filtrar por `tenant_id`
2. **Cascade:** Deletar tenant → soft delete (status='cancelled'), manter dados 5 anos (LGPD)
3. **Índices:** `tenant_id` + `created_at` em todas as tabelas de consulta frequente
4. **Encryption:** `bank_data` do Partner DEVE ser criptografado at rest
5. **Audit:** Toda alteração em Tenant e Partner DEVE gerar log de auditoria
