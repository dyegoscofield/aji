"""
Endpoints de billing — Stripe Checkout, Customer Portal, Webhook e status da assinatura.

Regras de segurança (CLAUDE.md seção 16):
- stripe_customer_id e stripe_subscription_id NUNCA aparecem em respostas de API
- Webhook validado via Stripe-Signature — sem assinatura válida, retorna 400 imediatamente
- Webhook SEMPRE retorna 200 ao Stripe (erros internos são logados, não propagados)
- Toda query ao banco filtra por tenant_id (multi-tenancy)
"""

import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.deps import get_current_active_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.services.billing.stripe_service import (
    VALID_PLANS,
    create_checkout_session,
    create_customer_portal_session,
    create_stripe_customer,
)
from app.services.billing.webhook_handler import dispatch_webhook_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Schemas Pydantic v2
# ---------------------------------------------------------------------------


class CheckoutRequest(BaseModel):
    plan: str

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, v: str) -> str:
        if v not in VALID_PLANS:
            raise ValueError(
                f"Plano '{v}' inválido. Opções: {', '.join(sorted(VALID_PLANS))}"
            )
        return v


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionStatus(BaseModel):
    plan: str
    status: str  # "trial" | "active" | "suspended" | "cancelled"
    trial_ends_at: datetime | None
    has_payment_method: bool


# ---------------------------------------------------------------------------
# Dependência de DB para endpoints autenticados
# ---------------------------------------------------------------------------


async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Inicia Stripe Checkout para assinar um plano",
)
async def create_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: AsyncSession = Depends(get_db_session),
) -> CheckoutResponse:
    """
    Cria uma Stripe Checkout Session para o tenant assinar o plano informado.

    Fluxo:
    1. Valida o plano (feito pelo schema).
    2. Se o tenant ainda não tem stripe_customer_id, cria o Customer no Stripe e salva.
    3. Cria a Checkout Session e retorna a URL.
    """
    # Passo 2: criar Customer no Stripe se necessário
    if not tenant.stripe_customer_id:
        customer_id = await create_stripe_customer(
            tenant_id=str(tenant.id),
            email=current_user.email,
            razao_social=tenant.razao_social,
            cnpj=tenant.cnpj,
        )
        # Multi-tenancy: tenant já está isolado via get_current_active_tenant
        tenant.stripe_customer_id = customer_id
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

    # Passo 3: criar Checkout Session
    checkout_url = await create_checkout_session(
        customer_id=tenant.stripe_customer_id,
        plan=body.plan,
        tenant_id=str(tenant.id),
    )

    return CheckoutResponse(checkout_url=checkout_url)


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Recebe eventos do Stripe via webhook",
    include_in_schema=False,  # não expor no Swagger — endpoint interno do Stripe
)
async def stripe_webhook(request: Request) -> dict:
    """
    Recebe e processa eventos do Stripe.

    Validação via Stripe-Signature obrigatória — sem assinatura válida, retorna 400.
    SEMPRE retorna 200 ao Stripe após validação, mesmo em erro interno.
    Erros de processamento são logados, nunca propagados como 5xx (Stripe faria retry).

    IMPORTANTE: usa `await request.body()` para obter os bytes brutos —
    o Stripe valida a assinatura sobre o payload original, não sobre JSON parseado.
    """
    payload: bytes = await request.body()
    sig_header: str | None = request.headers.get("stripe-signature")

    if not sig_header:
        logger.warning("Webhook recebido sem header Stripe-Signature — rejeitado")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header Stripe-Signature ausente",
        )

    # Validar assinatura — retorna 400 se inválida
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe-Signature inválida — webhook rejeitado")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assinatura do webhook inválida",
        )
    except Exception as exc:
        logger.error("Erro inesperado ao validar webhook Stripe: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload de webhook inválido",
        )

    # Processar evento — SEMPRE retornar 200 após assinatura validada
    try:
        async with AsyncSessionLocal() as db:
            await dispatch_webhook_event(event, db)
    except Exception as exc:
        # Logar e absorver — não retornar 5xx ao Stripe (causaria retry infinito)
        logger.error(
            "Erro interno ao processar evento Stripe %s: %s",
            event.type,
            repr(exc),
        )

    return {"status": "ok"}


@router.get(
    "/subscription",
    response_model=SubscriptionStatus,
    status_code=status.HTTP_200_OK,
    summary="Retorna o status da assinatura do tenant autenticado",
)
async def get_subscription(
    tenant: Tenant = Depends(get_current_active_tenant),
) -> SubscriptionStatus:
    """
    Retorna informações sobre a assinatura do tenant.

    Campos retornados:
    - plan: plano atual
    - status: "trial" | "active" | "suspended" | "cancelled"
    - trial_ends_at: data de expiração do trial (UTC)
    - has_payment_method: True se já possui assinatura Stripe ativa

    stripe_customer_id e stripe_subscription_id NÃO são retornados.
    """
    # Normaliza trial_ends_at para UTC aware
    trial_ends_at: datetime | None = tenant.trial_ends_at
    if trial_ends_at is not None and trial_ends_at.tzinfo is None:
        trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)

    return SubscriptionStatus(
        plan=tenant.plan,
        status=tenant.status,
        trial_ends_at=trial_ends_at,
        has_payment_method=tenant.stripe_subscription_id is not None,
    )


@router.post(
    "/portal",
    response_model=PortalResponse,
    status_code=status.HTTP_200_OK,
    summary="Abre o Stripe Customer Portal para gerenciar a assinatura",
)
async def open_customer_portal(
    tenant: Tenant = Depends(get_current_active_tenant),
) -> PortalResponse:
    """
    Cria uma sessão do Stripe Customer Portal para que o tenant gerencie
    sua assinatura (upgrade, downgrade, cancelamento, dados de pagamento).

    Requer que o tenant já tenha um stripe_customer_id — ou seja, que tenha
    iniciado ao menos uma Checkout Session anteriormente.
    """
    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Nenhuma assinatura Stripe encontrada. "
                "Acesse /billing/checkout para assinar um plano primeiro."
            ),
        )

    portal_url = await create_customer_portal_session(
        customer_id=tenant.stripe_customer_id,
        tenant_id=str(tenant.id),
    )

    return PortalResponse(portal_url=portal_url)
