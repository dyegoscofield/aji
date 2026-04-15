"""
Endpoints de autenticação do AJI.

Rotas:
  POST /api/v1/auth/register  — cadastro de empresa (Tenant + User owner)
  POST /api/v1/auth/login     — autenticação, retorna JWT
  GET  /api/v1/auth/me        — dados do usuário autenticado
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_tenant, get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserMeResponse,
)
from app.services.cnpj.brasilapi import fetch_cnpj_data, mask_cnpj

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar empresa",
    description="Cria um novo Tenant (empresa) e um usuário owner. "
    "O CNPJ é validado na Receita Federal via BrasilAPI. "
    "Trial de 7 dias inicia imediatamente sem necessidade de cartão.",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Fluxo:
    1. Limpa e valida CNPJ (formato + algoritmo módulo 11)
    2. Consulta BrasilAPI — obtém razao_social e verifica situação ATIVA
    3. Verifica se CNPJ já existe → 409
    4. Verifica se e-mail já existe → 409
    5. Cria Tenant (trial_ends_at = now + 7 dias)
    6. Cria User com role='owner' e senha hasheada
    7. Retorna JWT com user_id, tenant_id, role
    """
    cnpj = body.cnpj  # já normalizado pelo validator do schema

    # 1. Validar CNPJ na Receita Federal (levanta HTTPException se inválido/inativo)
    cnpj_data = await fetch_cnpj_data(cnpj)
    razao_social: str = cnpj_data.get("razao_social", "").strip()

    if not razao_social:
        logger.error("BrasilAPI retornou razao_social vazia para CNPJ %s", mask_cnpj(cnpj))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível obter os dados da empresa. Tente novamente.",
        )

    # 2. Verificar se CNPJ já existe — query SEM tenant_id (é a criação do tenant)
    existing_tenant = await db.execute(
        select(Tenant).where(Tenant.cnpj == cnpj)
    )
    if existing_tenant.scalar_one_or_none() is not None:
        logger.warning("Tentativa de cadastro com CNPJ duplicado: %s", mask_cnpj(cnpj))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CNPJ já cadastrado. Faça login ou recupere sua senha.",
        )

    # 3. Verificar se e-mail já existe (global, não por tenant — e-mail é identificador único)
    existing_user = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing_user.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado. Faça login ou use outro e-mail.",
        )

    # 4. Criar Tenant — trial_ends_at preenchido pelo default do model
    tenant = Tenant(
        cnpj=cnpj,
        razao_social=razao_social,
        plan="essencial",
        status="trial",
        # stripe_customer_id e stripe_subscription_id ficam NULL até webhook Stripe
    )
    db.add(tenant)
    await db.flush()  # gera tenant.id sem fechar a transação

    # 5. Criar User owner
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        role="owner",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(user)

    logger.info(
        "Novo tenant criado: razao_social='%s' cnpj=%s tenant_id=%s user_id=%s",
        razao_social,
        mask_cnpj(cnpj),
        tenant.id,
        user.id,
    )

    # 6. Gerar JWT
    access_token = create_access_token(
        data={
            "user_id": str(user.id),
            "tenant_id": str(tenant.id),
            "role": user.role,
        }
    )

    return RegisterResponse(
        access_token=access_token,
        token_type="bearer",
        tenant_id=tenant.id,
        razao_social=tenant.razao_social,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autenticar usuário",
    description="Autentica com e-mail e senha. Retorna JWT.",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Fluxo:
    1. Busca user por e-mail
    2. Verifica senha com bcrypt
    3. Verifica que user está ativo
    4. Retorna JWT
    """
    # Buscar user por e-mail (e-mail é único globalmente)
    result = await db.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()

    # Falha genérica para não vazar se o e-mail existe ou não
    _auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="E-mail ou senha incorretos",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        raise _auth_error

    if not verify_password(body.password, user.hashed_password):
        raise _auth_error

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo. Entre em contato com o suporte.",
        )

    logger.info("Login bem-sucedido: user_id=%s tenant_id=%s", user.id, user.tenant_id)

    access_token = create_access_token(
        data={
            "user_id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
        }
    )

    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post(
    "/login/form",
    response_model=TokenResponse,
    include_in_schema=False,  # endpoint interno para compatibilidade OAuth2 do Swagger UI
)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Endpoint OAuth2 form para o Swagger UI 'Authorize'. Delega para /login."""
    from app.schemas.auth import LoginRequest as _LR
    return await login(_LR(email=form_data.username, password=form_data.password), db)


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Dados do usuário autenticado",
    description="Retorna dados do usuário e do tenant. Requer Bearer token válido.",
)
async def me(
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_active_tenant),
) -> UserMeResponse:
    """
    Retorna dados do usuário autenticado e do tenant associado.
    Campos sensíveis (CNPJ completo, stripe IDs) são omitidos da resposta.
    """
    return UserMeResponse(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        razao_social=current_tenant.razao_social,
        plan=current_tenant.plan,
        status=current_tenant.status,
    )
