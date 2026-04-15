---
name: stripe-webhooks
description: |
  Implementa webhook handlers do Stripe com verificação de assinatura, parse de eventos
  e lógica de negócio para assinaturas SaaS. Use sempre que precisar implementar ou
  modificar a integração Stripe no AJI. Inclui padrões para invoice.paid,
  subscription.deleted e payment_failed.
---

## Verificação de assinatura (obrigatório)

```python
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    await handle_event(event)
    return {"status": "ok"}
```

## Eventos críticos do AJI

```python
async def handle_event(event: stripe.Event):
    match event.type:
        case "invoice.paid":
            await on_invoice_paid(event.data.object)
        case "invoice.payment_failed":
            await on_payment_failed(event.data.object)
        case "customer.subscription.deleted":
            await on_subscription_cancelled(event.data.object)
        case "customer.subscription.updated":
            await on_subscription_updated(event.data.object)

async def on_invoice_paid(invoice):
    tenant_id = invoice.metadata["tenant_id"]
    await TenantRepository.update(tenant_id, {"status": "active"})
    # Pagar comissão do parceiro
    if partner_id := await get_partner_for_tenant(tenant_id):
        await CommissionRepository.create(partner_id, invoice.amount_paid * 0.20)
```

## Gotchas
- Sempre retornar 200 para o Stripe (mesmo em erro de negócio)
- Idempotência: checar se evento já foi processado pelo ID
- Usar metadata do Stripe para guardar tenant_id e partner_id
- Testar localmente com: `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`
