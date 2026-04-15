"""
Handler de webhooks do Stripe.

Regras críticas:
- Toda query ao banco DEVE filtrar por tenant_id (multi-tenancy — CLAUDE.md seção 16)
- O endpoint que chama dispatch_webhook_event() SEMPRE retorna 200 ao Stripe,
  mesmo que ocorra erro interno aqui. Erros são logados, não propagados como 5xx.
- stripe_customer_id e stripe_subscription_id NUNCA aparecem em logs.
"""

import logging
import uuid

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


async def _get_tenant_by_id(
    db: AsyncSession, tenant_id_str: str
) -> Tenant | None:
    """Busca Tenant pelo UUID. Retorna None se não encontrado ou UUID inválido.

    Multi-tenancy: filtra exclusivamente pelo tenant_id extraído do metadata
    do evento Stripe — nunca por dados do cliente Stripe.
    """
    try:
        tenant_uuid = uuid.UUID(tenant_id_str)
    except (ValueError, AttributeError):
        logger.error(
            "tenant_id inválido no metadata do evento Stripe: %r", tenant_id_str
        )
        return None

    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_uuid,  # OBRIGATÓRIO — multi-tenancy
        )
    )
    return result.scalar_one_or_none()


async def handle_checkout_completed(
    event_data: dict, db: AsyncSession
) -> None:
    """Processa checkout.session.completed.

    Atualiza stripe_subscription_id, plan e status do tenant para "active".
    O stripe_customer_id já foi salvo no momento da criação do Customer.
    """
    session = event_data.get("object", {})
    tenant_id_str: str = session.get("metadata", {}).get("tenant_id", "")
    plan: str = session.get("metadata", {}).get("plan", "")
    subscription_id: str | None = session.get("subscription")

    if not tenant_id_str or not plan:
        logger.error(
            "checkout.session.completed sem tenant_id ou plan no metadata"
        )
        return

    tenant = await _get_tenant_by_id(db, tenant_id_str)
    if tenant is None:
        logger.error(
            "Tenant não encontrado para tenant_id=%s (checkout.session.completed)",
            tenant_id_str,
        )
        return

    tenant.plan = plan
    tenant.status = "active"
    if subscription_id:
        tenant.stripe_subscription_id = subscription_id

    await db.commit()
    logger.info(
        "checkout.session.completed processado — tenant_id=%s plano=%s status=active",
        tenant_id_str,
        plan,
    )


async def handle_subscription_updated(
    event_data: dict, db: AsyncSession
) -> None:
    """Processa customer.subscription.updated.

    Mapeia o status do Stripe para o status interno do AJI:
    - active   → active
    - past_due → suspended
    - unpaid   → suspended

    Se o plano mudou (upgrade/downgrade via Customer Portal), atualiza o plan.
    """
    subscription = event_data.get("object", {})
    stripe_status: str = subscription.get("status", "")
    tenant_id_str: str = subscription.get("metadata", {}).get("tenant_id", "")

    # Mapeia status do Stripe para status interno
    STATUS_MAP: dict[str, str] = {
        "active": "active",
        "past_due": "suspended",
        "unpaid": "suspended",
    }
    new_status = STATUS_MAP.get(stripe_status)

    if not tenant_id_str:
        logger.warning(
            "customer.subscription.updated sem tenant_id no metadata — ignorado"
        )
        return

    tenant = await _get_tenant_by_id(db, tenant_id_str)
    if tenant is None:
        logger.error(
            "Tenant não encontrado para tenant_id=%s (subscription.updated)",
            tenant_id_str,
        )
        return

    if new_status:
        tenant.status = new_status

    # Verificar se o plano mudou via Customer Portal
    items = subscription.get("items", {}).get("data", [])
    if items:
        price_id: str = items[0].get("price", {}).get("id", "")
        # Importação local para evitar dependência circular no módulo de serviço
        from app.services.billing.stripe_service import PLAN_PRICE_MAP

        plan_by_price = {v: k for k, v in PLAN_PRICE_MAP.items()}
        new_plan = plan_by_price.get(price_id)
        if new_plan and new_plan != tenant.plan:
            logger.info(
                "Plano alterado via portal para tenant_id=%s: %s → %s",
                tenant_id_str,
                tenant.plan,
                new_plan,
            )
            tenant.plan = new_plan

    await db.commit()
    logger.info(
        "subscription.updated processado — tenant_id=%s stripe_status=%s status_interno=%s",
        tenant_id_str,
        stripe_status,
        new_status or "(não mapeado)",
    )


async def handle_subscription_deleted(
    event_data: dict, db: AsyncSession
) -> None:
    """Processa customer.subscription.deleted.

    Define status do tenant como "cancelled" e limpa o stripe_subscription_id.
    """
    subscription = event_data.get("object", {})
    tenant_id_str: str = subscription.get("metadata", {}).get("tenant_id", "")

    if not tenant_id_str:
        logger.warning(
            "customer.subscription.deleted sem tenant_id no metadata — ignorado"
        )
        return

    tenant = await _get_tenant_by_id(db, tenant_id_str)
    if tenant is None:
        logger.error(
            "Tenant não encontrado para tenant_id=%s (subscription.deleted)",
            tenant_id_str,
        )
        return

    tenant.status = "cancelled"
    tenant.stripe_subscription_id = None

    await db.commit()
    logger.info(
        "subscription.deleted processado — tenant_id=%s status=cancelled",
        tenant_id_str,
    )


async def handle_invoice_payment_failed(
    event_data: dict, db: AsyncSession
) -> None:
    """Processa invoice.payment_failed.

    Define status do tenant como "suspended".
    Em produção: disparar e-mail de cobrança via Celery task.
    Por ora, apenas atualiza o status no banco.
    """
    invoice = event_data.get("object", {})
    # invoice não carrega tenant_id diretamente — buscar via subscription metadata
    subscription_id: str | None = invoice.get("subscription")

    # Estratégia: recuperar tenant via stripe_subscription_id
    # O metadata do invoice não tem tenant_id, mas a subscription tem.
    # Usamos o subscription_id para localizar o tenant no banco de dados.
    if not subscription_id:
        logger.warning(
            "invoice.payment_failed sem subscription_id — ignorado"
        )
        return

    result = await db.execute(
        select(Tenant).where(
            Tenant.stripe_subscription_id == subscription_id,
        )
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        logger.error(
            "Tenant não encontrado para subscription_id no invoice.payment_failed"
        )
        return

    tenant.status = "suspended"
    await db.commit()

    # TODO (produção): disparar Celery task para envio de e-mail de cobrança
    logger.info(
        "invoice.payment_failed processado — tenant_id=%s status=suspended",
        str(tenant.id),
    )


async def dispatch_webhook_event(
    event: stripe.Event, db: AsyncSession
) -> None:
    """Router de eventos Stripe.

    Delega para o handler correto conforme event.type.
    Eventos não mapeados são logados e ignorados sem erro.
    """
    event_data: dict = event.data  # type: ignore[assignment]

    handlers = {
        "checkout.session.completed": handle_checkout_completed,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_deleted,
        "invoice.payment_failed": handle_invoice_payment_failed,
    }

    handler = handlers.get(event.type)
    if handler is None:
        logger.debug("Evento Stripe não tratado: %s — ignorado", event.type)
        return

    logger.info("Processando evento Stripe: %s", event.type)
    await handler(event_data, db)
