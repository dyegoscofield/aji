---
name: aji-multitenant-guard
description: |
  Garante isolamento correto entre tenants no AJI. Use ao revisar qualquer query de banco
  de dados, endpoint de API, ou lógica de negócio que acesse dados. Previne vazamento
  cross-tenant — o maior risco de segurança de um SaaS multi-tenant.
---

## Regra absoluta

TODA query ao banco deve filtrar por tenant_id. Sem exceção.

## Padrão obrigatório

```python
# CORRETO — sempre filtrar por tenant_id
result = await db.execute(
    select(Conversation)
    .where(Conversation.tenant_id == current_tenant.id)
    .where(Conversation.id == conversation_id)
)

# ERRADO — nunca buscar só pelo ID sem tenant
result = await db.execute(
    select(Conversation).where(Conversation.id == conversation_id)
)
```

## Checklist de revisão

Ao revisar qualquer endpoint ou service, verificar:

- [ ] Todo `SELECT` tem `.where(Model.tenant_id == tenant_id)`
- [ ] Resources retornados pertencem ao tenant do token JWT
- [ ] Erros de "não encontrado" retornam 404 (não 403) — não revelar existência
- [ ] LegalChunks: busca inclui `(tenant_id IS NULL OR tenant_id = ?)` (global + privado)
- [ ] Nenhum endpoint admin acessível por usuário comum

## Scan rápido

```bash
# Encontrar selects sem filtro tenant_id (revisar manualmente)
grep -n "select(" backend/app/repositories/*.py | grep -v "tenant_id"
```
