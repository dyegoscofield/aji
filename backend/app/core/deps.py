"""
Dependências de injeção para FastAPI.

Regra crítica de multi-tenancy: toda query ao banco DEVE incluir tenant_id como filtro.
"""

import uuid
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciais inválidas ou sessão expirada",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decodifica o JWT e retorna o usuário autenticado.

    A query filtra por user.id E user.tenant_id — ambos extraídos do token —
    garantindo isolamento multi-tenant mesmo que o user_id seja adivinhado.
    """
    payload = decode_token(token)
    if payload is None:
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(str(payload["user_id"]))
        tenant_id = uuid.UUID(str(payload["tenant_id"]))
    except (KeyError, ValueError):
        raise _CREDENTIALS_EXCEPTION

    # Multi-tenancy: filtrar por ambos user.id e user.tenant_id
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,  # OBRIGATÓRIO — multi-tenancy
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise _CREDENTIALS_EXCEPTION

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo",
        )

    return user


async def get_current_active_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """
    Retorna o Tenant do usuário autenticado.

    Levanta 403 se o tenant estiver suspenso ou cancelado.
    """
    # Multi-tenancy: filtrar por tenant.id correspondente ao usuário
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == current_user.tenant_id,  # OBRIGATÓRIO — multi-tenancy
        )
    )
    tenant = result.scalar_one_or_none()

    if tenant is None:
        logger.error(
            "Tenant não encontrado para user_id=%s tenant_id=%s",
            current_user.id,
            current_user.tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não encontrado",
        )

    if tenant.status in ("suspended", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado — conta com status '{tenant.status}'. "
            "Entre em contato com o suporte.",
        )

    return tenant
