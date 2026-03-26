# Integração Stripe (Assinaturas e Billing)

## Planos e Preços

```python
PLANS = {
    "essencial":      {"price_id": "price_xxx_essencial",   "amount": 19700},
    "profissional":   {"price_id": "price_xxx_profissional", "amount": 29700},
    "personalizado":  {"price_id": "price_xxx_personalizado","amount": 39700},
}
```

## Criação de Assinatura

```python
# app/services/billing.py

import stripe

class StripeService:
    
    @staticmethod
    async def create_subscription(tenant: Tenant, plan: str) -> stripe.Subscription:
        subscription = stripe.Subscription.create(
            customer=tenant.stripe_customer_id,
            items=[{"price": PLANS[plan]["price_id"]}],
            trial_end=int(tenant.trial_ends_at.timestamp()) if tenant.status == "trial" else "now",
            metadata={
                "tenant_id": str(tenant.id),
                "cnpj": tenant.cnpj,
                "plan": plan,
            }
        )
        return subscription
    
    @staticmethod
    async def handle_webhook(payload: bytes, sig: str):
        """
        Eventos importantes:
        - customer.subscription.updated → atualizar plano
        - customer.subscription.deleted → suspender tenant
        - invoice.paid → confirmar pagamento + pagar comissão parceiro
        - invoice.payment_failed → notificar + grace period de 3 dias
        """
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
        
        if event.type == "invoice.paid":
            await BillingService.process_payment(event.data.object)
            await PartnerService.process_commission(event.data.object)
        
        elif event.type == "customer.subscription.deleted":
            tenant_id = event.data.object.metadata["tenant_id"]
            await TenantRepository.update(db, tenant_id, {"status": "cancelled"})
```

## Canal de Parceiros — Comissão

Escritórios de contabilidade recebem **20% de comissão recorrente** enquanto o cliente permanecer ativo. No MVP, controle via planilha + pagamento PIX. Portal do parceiro fica para fase 2.

## Regras Críticas

1. **NUNCA expor `stripe_customer_id` ou `stripe_subscription_id` em logs ou respostas de API** — ver CLAUDE.md seção 16
2. Webhook DEVE validar assinatura Stripe antes de processar
3. Grace period de 3 dias para pagamento falhado antes de suspender
4. Comissão do parceiro é calculada sobre o valor líquido (sem impostos)
