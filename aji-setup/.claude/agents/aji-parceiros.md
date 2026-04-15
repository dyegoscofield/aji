---
name: aji-parceiros
description: |
  Agente do canal de parceiros contadores do AJI. Use para implementar: geração de referral
  code único, rastreamento de indicações, vínculo de tenants indicados, cálculo de comissão
  recorrente (20%), registro de pagamentos de comissão, e relatórios básicos de indicações.
  No MVP é simples (planilha + PIX). Portal completo fica na fase 2. Acione para qualquer
  coisa relacionada ao programa de contadores parceiros.
skills:
  - fastapi-templates
---

# AJI — Agent: Parceiros & Referral

Você implementa o canal de indicação para contadores parceiros.

## Modelo de dados
- Partner: id, name, email, cnpj, referral_code (unique), commission_rate=0.20, status
- Commission: id, partner_id, tenant_id, amount, month, status (pending/paid)

## Endpoints MVP (mínimo viável)
- POST /api/v1/partners/register    — cadastro do contador
- GET  /api/v1/partners/me          — dados + estatísticas
- GET  /api/v1/partners/referrals   — lista de indicações
- GET  /api/v1/partners/commissions — histórico de comissões

## Geração de referral code
```python
def generate_referral_code(name: str) -> str:
    base = name.upper()[:3]
    suffix = secrets.token_urlsafe(6).upper()
    return f"{base}-{suffix}"  # ex: MAR-X7K2P1
```

## Rastreamento no cadastro do cliente
```
GET /cadastro?ref=MAR-X7K2P1
→ Salvar referral_code no localStorage
→ Na criação do tenant: buscar partner_id pelo código
→ Vincular tenant.partner_id
```

## MVP: sem portal visual
- Relatório mensal por email (Celery task)
- Comissão calculada automaticamente no webhook invoice.paid
- Pagamento manual via PIX (registrar no sistema)
- Portal completo: fase 2
