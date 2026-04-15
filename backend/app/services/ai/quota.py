"""
Controle de quota de consultas por plano e por tenant.

Limites (CLAUDE.md seção 6):
- essencial:     30 consultas/mês
- profissional:  ilimitado
- personalizado: ilimitado

Regra crítica de multi-tenancy: toda query DEVE incluir tenant_id.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

PLAN_LIMITS: dict[str, int | None] = {
    "essencial": 30,
    "profissional": None,   # ilimitado
    "personalizado": None,  # ilimitado
}


async def get_monthly_usage(tenant_id: uuid.UUID, db: AsyncSession) -> int:
    """
    Conta mensagens com role="user" do tenant no mês corrente.

    Regra de multi-tenancy: filtra obrigatoriamente por tenant_id.
    Conta apenas mensagens do usuário (role="user") como "consultas"
    — mensagens do assistente não contam contra a quota.

    Args:
        tenant_id: UUID do tenant autenticado.
        db:        Sessão assíncrona do banco de dados.

    Returns:
        Número de consultas realizadas no mês corrente.
    """
    now = datetime.now(timezone.utc)
    # Primeiro dia do mês corrente, meia-noite UTC
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(Message.id)).where(
            Message.tenant_id == tenant_id,      # OBRIGATÓRIO — multi-tenancy
            Message.role == "user",
            Message.created_at >= month_start,
        )
    )
    count: int = result.scalar_one()
    return count


async def check_quota(tenant: Tenant, db: AsyncSession) -> None:
    """
    Verifica se o tenant tem quota disponível para uma nova consulta.

    Levanta HTTPException antes de processar a mensagem para evitar
    custos de API desnecessários quando o limite está atingido.

    Ordem de verificação:
    1. Trial expirado → 402 Payment Required
    2. Quota mensal atingida (apenas plano essencial) → 429 Too Many Requests

    Args:
        tenant: Objeto Tenant do usuário autenticado.
        db:     Sessão assíncrona do banco de dados.

    Raises:
        HTTPException(402): Trial expirado sem assinatura ativa.
        HTTPException(429): Limite mensal de consultas atingido.
    """
    # Verificar trial expirado (apenas status "trial")
    if tenant.status == "trial":
        now = datetime.now(timezone.utc)
        # trial_ends_at pode ser naive (sem tz) — normalizar para UTC
        trial_ends = tenant.trial_ends_at
        if trial_ends.tzinfo is None:
            trial_ends = trial_ends.replace(tzinfo=timezone.utc)

        if now > trial_ends:
            logger.warning(
                "Acesso negado — trial expirado para tenant_id=%s", tenant.id
            )
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "TRIAL_EXPIRED",
                    "message": (
                        "Seu período de teste gratuito expirou. "
                        "Assine um plano para continuar usando o AJI."
                    ),
                    "upgrade_url": "/planos",
                },
            )

    # Verificar quota mensal (apenas plano com limite)
    limit = PLAN_LIMITS.get(tenant.plan)
    if limit is not None:
        usage = await get_monthly_usage(tenant.id, db)
        if usage >= limit:
            logger.warning(
                "Quota mensal atingida para tenant_id=%s (uso=%d, limite=%d, plano=%s)",
                tenant.id,
                usage,
                limit,
                tenant.plan,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "message": (
                        f"Limite de {limit} consultas mensais atingido. "
                        "Faça upgrade para o plano Profissional para consultas ilimitadas."
                    ),
                    "current_usage": usage,
                    "limit": limit,
                    "upgrade_url": "/planos",
                },
            )
