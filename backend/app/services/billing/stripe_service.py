"""
Serviço de integração com Stripe.

Regras de segurança (CLAUDE.md seção 16):
- stripe_customer_id e stripe_subscription_id NUNCA aparecem em logs ou respostas de API
- CNPJ passado ao Stripe SEMPRE mascarado via mask_cnpj()
- AuthenticationError tratado como 503 — keys placeholder em dev não quebram o boot
"""

import logging

import stripe
from fastapi import HTTPException

from app.core.config import settings
from app.services.cnpj.brasilapi import mask_cnpj

logger = logging.getLogger(__name__)

# Inicialização da API key. Em dev, a key pode ser placeholder — os métodos
# abaixo tratam AuthenticationError graciosamente.
stripe.api_key = settings.STRIPE_SECRET_KEY

PLAN_PRICE_MAP: dict[str, str] = {
    "essencial": settings.STRIPE_PRICE_ESSENCIAL,
    "profissional": settings.STRIPE_PRICE_PROFISSIONAL,
    "personalizado": settings.STRIPE_PRICE_PERSONALIZADO,
}

VALID_PLANS = frozenset(PLAN_PRICE_MAP.keys())


def get_price_id(plan: str) -> str:
    """Retorna o price_id do Stripe para o plano informado.

    Raises:
        ValueError: se o plano não for reconhecido.
    """
    if plan not in PLAN_PRICE_MAP:
        raise ValueError(
            f"Plano '{plan}' inválido. Opções: {', '.join(VALID_PLANS)}"
        )
    return PLAN_PRICE_MAP[plan]


async def create_stripe_customer(
    tenant_id: str,
    email: str,
    razao_social: str,
    cnpj: str,  # CNPJ bruto — será mascarado antes de sair do sistema
) -> str:
    """Cria um Customer no Stripe e retorna o stripe_customer_id.

    O CNPJ é sempre mascarado no metadata enviado ao Stripe.
    Nunca loga o stripe_customer_id retornado.

    Args:
        tenant_id: UUID do tenant no AJI.
        email: e-mail do usuário owner do tenant.
        razao_social: razão social da empresa.
        cnpj: CNPJ bruto (14 dígitos ou formatado).

    Returns:
        stripe_customer_id (str), ex: "cus_xxx".

    Raises:
        HTTPException(503): se a API do Stripe estiver indisponível ou a key for inválida.
    """
    cnpj_masked = mask_cnpj(cnpj)
    logger.info(
        "Criando Customer no Stripe para tenant_id=%s cnpj=%s",
        tenant_id,
        cnpj_masked,
    )
    try:
        customer = stripe.Customer.create(
            email=email,
            name=razao_social,
            metadata={
                "tenant_id": tenant_id,
                "cnpj": cnpj_masked,  # mascarado — nunca o CNPJ completo
            },
        )
    except stripe.error.AuthenticationError:
        logger.error(
            "Stripe AuthenticationError ao criar Customer para tenant_id=%s "
            "— verifique STRIPE_SECRET_KEY",
            tenant_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Serviço de pagamentos indisponível. Tente novamente mais tarde.",
        )
    except stripe.error.StripeError as exc:
        logger.error(
            "StripeError ao criar Customer para tenant_id=%s: %s",
            tenant_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Serviço de pagamentos indisponível. Tente novamente mais tarde.",
        )

    # Nunca logar o customer_id completo
    logger.info("Customer Stripe criado para tenant_id=%s", tenant_id)
    return customer.id


async def create_checkout_session(
    customer_id: str,
    plan: str,
    tenant_id: str,
) -> str:
    """Cria uma Stripe Checkout Session e retorna a URL de redirecionamento.

    O trial já ocorre dentro do produto AJI — o Checkout cobra imediatamente
    (trial_period_days=0). O plano pode ser trocado via Customer Portal.

    Args:
        customer_id: stripe_customer_id do tenant.
        plan: "essencial" | "profissional" | "personalizado".
        tenant_id: UUID do tenant no AJI (incluído no metadata para o webhook).

    Returns:
        URL do Stripe Checkout (str).

    Raises:
        HTTPException(400): plano inválido.
        HTTPException(503): Stripe indisponível ou key inválida.
    """
    try:
        price_id = get_price_id(plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info(
        "Criando Checkout Session para tenant_id=%s plano=%s", tenant_id, plan
    )
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            # trial já foi dado pelo produto — cobrar imediatamente
            subscription_data={"trial_period_days": 0},
            success_url=(
                f"{settings.FRONTEND_URL}/dashboard?checkout=success"
            ),
            cancel_url=(
                f"{settings.FRONTEND_URL}/planos?checkout=cancelled"
            ),
            metadata={
                "tenant_id": tenant_id,
                "plan": plan,
            },
        )
    except stripe.error.AuthenticationError:
        logger.error(
            "Stripe AuthenticationError ao criar Checkout Session para tenant_id=%s",
            tenant_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Serviço de pagamentos indisponível. Tente novamente mais tarde.",
        )
    except stripe.error.StripeError as exc:
        logger.error(
            "StripeError ao criar Checkout Session para tenant_id=%s: %s",
            tenant_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Serviço de pagamentos indisponível. Tente novamente mais tarde.",
        )

    logger.info("Checkout Session criada para tenant_id=%s", tenant_id)
    return session.url


async def create_customer_portal_session(
    customer_id: str,
    tenant_id: str,
) -> str:
    """Cria uma sessão do Stripe Customer Portal para o tenant gerenciar a assinatura.

    Permite upgrade, downgrade e cancelamento sem intervenção manual.

    Args:
        customer_id: stripe_customer_id do tenant.
        tenant_id: UUID do tenant no AJI (usado apenas em logs).

    Returns:
        URL do Customer Portal (str).

    Raises:
        HTTPException(503): Stripe indisponível ou key inválida.
    """
    logger.info(
        "Criando Customer Portal Session para tenant_id=%s", tenant_id
    )
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard",
        )
    except stripe.error.AuthenticationError:
        logger.error(
            "Stripe AuthenticationError ao criar Portal Session para tenant_id=%s",
            tenant_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Serviço de pagamentos indisponível. Tente novamente mais tarde.",
        )
    except stripe.error.StripeError as exc:
        logger.error(
            "StripeError ao criar Portal Session para tenant_id=%s: %s",
            tenant_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Serviço de pagamentos indisponível. Tente novamente mais tarde.",
        )

    logger.info("Customer Portal Session criada para tenant_id=%s", tenant_id)
    return portal_session.url


async def cancel_subscription(subscription_id: str) -> None:
    """Cancela a assinatura no Stripe ao fim do período pago.

    Usa cancel_at_period_end=True — o acesso permanece até o fim do ciclo já pago.
    O webhook customer.subscription.deleted é disparado pelo Stripe quando o
    período encerrar de fato.

    Args:
        subscription_id: stripe_subscription_id da assinatura.

    Raises:
        HTTPException(503): Stripe indisponível ou key inválida.
    """
    logger.info("Agendando cancelamento de assinatura no Stripe (cancel_at_period_end)")
    try:
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
        )
    except stripe.error.AuthenticationError:
        logger.error("Stripe AuthenticationError ao cancelar assinatura")
        raise HTTPException(
            status_code=503,
            detail="Serviço de pagamentos indisponível. Tente novamente mais tarde.",
        )
    except stripe.error.StripeError as exc:
        logger.error(
            "StripeError ao cancelar assinatura: %s", type(exc).__name__
        )
        raise HTTPException(
            status_code=503,
            detail="Serviço de pagamentos indisponível. Tente novamente mais tarde.",
        )
    logger.info("Cancelamento agendado com sucesso (cancel_at_period_end=True)")
