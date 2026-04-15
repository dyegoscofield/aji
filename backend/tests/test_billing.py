"""
Testes do módulo de billing — Stripe Checkout, Customer Portal, Webhook e status.

Estrutura:
- TestCheckoutEndpoint       : POST /api/v1/billing/checkout
- TestWebhookEndpoint        : POST /api/v1/billing/webhook
- TestSubscriptionEndpoint   : GET /api/v1/billing/subscription
- TestPortalEndpoint         : POST /api/v1/billing/portal
- TestWebhookHandlers        : handlers internos (checkout_completed, subscription_*)
- TestStripeService          : funções do stripe_service

Todos os testes mockam a API do Stripe — nenhuma chamada real é feita.
Não dependem de banco real.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def make_mock_user(tenant_id: uuid.UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.tenant_id = tenant_id or uuid.uuid4()
    user.is_active = True
    user.email = "owner@empresa.com.br"
    return user


def make_mock_tenant(
    plan: str = "profissional",
    status: str = "active",
    tenant_id: uuid.UUID | None = None,
    stripe_customer_id: str | None = "cus_test_123",
    stripe_subscription_id: str | None = "sub_test_456",
) -> MagicMock:
    tenant = MagicMock()
    tenant.id = tenant_id or uuid.uuid4()
    tenant.plan = plan
    tenant.status = status
    tenant.razao_social = "Empresa Teste Ltda"
    tenant.cnpj = "12345678000195"
    tenant.stripe_customer_id = stripe_customer_id
    tenant.stripe_subscription_id = stripe_subscription_id
    tenant.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=7)
    return tenant


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer fake-token-qualquer"}


@pytest.fixture(autouse=True)
def clear_overrides():
    """Limpa dependency_overrides após cada teste para não vazar entre testes."""
    yield
    app.dependency_overrides.clear()


def setup_auth(
    plan: str = "profissional",
    stripe_customer_id: str | None = "cus_test_123",
    stripe_subscription_id: str | None = "sub_test_456",
    tenant_status: str = "active",
) -> tuple[MagicMock, MagicMock]:
    from app.core.deps import get_current_active_tenant, get_current_user

    tid = uuid.uuid4()
    mock_user = make_mock_user(tenant_id=tid)
    mock_tenant = make_mock_tenant(
        plan=plan,
        status=tenant_status,
        tenant_id=tid,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_active_tenant] = lambda: mock_tenant

    return mock_user, mock_tenant


# ---------------------------------------------------------------------------
# TestCheckoutEndpoint — POST /api/v1/billing/checkout
# ---------------------------------------------------------------------------


class TestCheckoutEndpoint:
    @pytest.mark.asyncio
    async def test_checkout_plano_valido_retorna_url(self):
        """POST /checkout com plano válido e customer existente → 200 com checkout_url."""
        setup_auth(stripe_customer_id="cus_test_123")

        mock_session_url = "https://checkout.stripe.com/pay/cs_test_abc"

        with patch(
            "app.services.billing.stripe_service.stripe.checkout.Session.create"
        ) as mock_create:
            mock_create.return_value = MagicMock(url=mock_session_url)

            # Mock da sessão do banco — tenant já tem customer_id, não precisa criar
            mock_db = AsyncMock()
            with patch(
                "app.api.v1.billing.AsyncSessionLocal",
                return_value=MagicMock(
                    __aenter__=AsyncMock(return_value=mock_db),
                    __aexit__=AsyncMock(return_value=False),
                ),
            ):
                with patch(
                    "app.api.v1.billing.get_db_session",
                    return_value=AsyncMock(__anext__=AsyncMock(return_value=mock_db)),
                ):
                    async with AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        response = await client.post(
                            "/api/v1/billing/checkout",
                            json={"plan": "profissional"},
                            headers=auth_headers(),
                        )

        assert response.status_code == 200
        data = response.json()
        assert "checkout_url" in data
        assert data["checkout_url"] == mock_session_url

    @pytest.mark.asyncio
    async def test_checkout_plano_invalido_retorna_422(self):
        """POST /checkout com plano inválido → 422 (Pydantic validation)."""
        setup_auth()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/billing/checkout",
                json={"plan": "plano_inexistente"},
                headers=auth_headers(),
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_checkout_sem_autenticacao_retorna_401(self):
        """POST /checkout sem token → 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/billing/checkout",
                json={"plan": "essencial"},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_checkout_cria_customer_quando_ausente(self):
        """POST /checkout sem stripe_customer_id → cria Customer no Stripe antes do checkout."""
        mock_user, mock_tenant = setup_auth(stripe_customer_id=None)

        novo_customer_id = "cus_novo_456"
        mock_session_url = "https://checkout.stripe.com/pay/cs_test_xyz"

        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch(
            "app.services.billing.stripe_service.stripe.Customer.create"
        ) as mock_customer_create, patch(
            "app.services.billing.stripe_service.stripe.checkout.Session.create"
        ) as mock_session_create, patch(
            "app.api.v1.billing.get_db_session"
        ) as mock_get_db:
            mock_customer_create.return_value = MagicMock(id=novo_customer_id)
            mock_session_create.return_value = MagicMock(url=mock_session_url)

            # Simula o generator do Depends(get_db_session)
            async def fake_db_gen():
                yield mock_db

            mock_get_db.return_value = fake_db_gen()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/billing/checkout",
                    json={"plan": "essencial"},
                    headers=auth_headers(),
                )

        # Deve ter chamado create_stripe_customer
        mock_customer_create.assert_called_once()
        # E criado a Checkout Session
        mock_session_create.assert_called_once()


# ---------------------------------------------------------------------------
# TestWebhookEndpoint — POST /api/v1/billing/webhook
# ---------------------------------------------------------------------------


def _make_stripe_event(event_type: str, metadata: dict | None = None) -> MagicMock:
    """Cria um mock de stripe.Event para uso nos testes de webhook."""
    event = MagicMock()
    event.type = event_type
    event.data = {
        "object": {
            "metadata": metadata or {},
            "status": "active",
            "subscription": "sub_test_123",
            "items": {"data": []},
        }
    }
    return event


class TestWebhookEndpoint:
    @pytest.mark.asyncio
    async def test_webhook_assinatura_valida_retorna_200(self):
        """POST /webhook com Stripe-Signature válida → 200 {"status": "ok"}."""
        mock_event = _make_stripe_event("customer.subscription.updated")

        with patch(
            "app.api.v1.billing.stripe.Webhook.construct_event",
            return_value=mock_event,
        ), patch(
            "app.api.v1.billing.dispatch_webhook_event",
            new_callable=AsyncMock,
        ) as mock_dispatch, patch(
            "app.api.v1.billing.AsyncSessionLocal"
        ) as mock_session_local:
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/billing/webhook",
                    content=b'{"type":"customer.subscription.updated"}',
                    headers={"stripe-signature": "t=1234,v1=abc"},
                )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_dispatch.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_assinatura_invalida_retorna_400(self):
        """POST /webhook com assinatura inválida → 400."""
        import stripe as stripe_lib

        with patch(
            "app.api.v1.billing.stripe.Webhook.construct_event",
            side_effect=stripe_lib.error.SignatureVerificationError(
                "Invalid signature", sig_header="bad"
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/billing/webhook",
                    content=b"payload_qualquer",
                    headers={"stripe-signature": "assinatura_invalida"},
                )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_sem_signature_header_retorna_400(self):
        """POST /webhook sem header Stripe-Signature → 400."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/billing/webhook",
                content=b"payload_qualquer",
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_erro_interno_ainda_retorna_200(self):
        """POST /webhook com erro interno no handler → ainda retorna 200 (não retentar)."""
        mock_event = _make_stripe_event("checkout.session.completed")

        with patch(
            "app.api.v1.billing.stripe.Webhook.construct_event",
            return_value=mock_event,
        ), patch(
            "app.api.v1.billing.dispatch_webhook_event",
            new_callable=AsyncMock,
            side_effect=Exception("Erro interno simulado"),
        ), patch(
            "app.api.v1.billing.AsyncSessionLocal"
        ) as mock_session_local:
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/billing/webhook",
                    content=b'{"type":"checkout.session.completed"}',
                    headers={"stripe-signature": "t=1234,v1=abc"},
                )

        # Mesmo com erro interno, Stripe deve receber 200
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# TestSubscriptionEndpoint — GET /api/v1/billing/subscription
# ---------------------------------------------------------------------------


class TestSubscriptionEndpoint:
    @pytest.mark.asyncio
    async def test_subscription_retorna_dados_corretos(self):
        """GET /subscription → retorna plan, status, trial_ends_at, has_payment_method."""
        _, mock_tenant = setup_auth(
            plan="profissional",
            tenant_status="active",
            stripe_subscription_id="sub_test_789",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/billing/subscription",
                headers=auth_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "profissional"
        assert data["status"] == "active"
        assert data["has_payment_method"] is True
        assert "trial_ends_at" in data

    @pytest.mark.asyncio
    async def test_subscription_sem_payment_method(self):
        """GET /subscription com tenant sem stripe_subscription_id → has_payment_method=False."""
        setup_auth(
            plan="essencial",
            tenant_status="trial",
            stripe_subscription_id=None,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/billing/subscription",
                headers=auth_headers(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["has_payment_method"] is False
        assert data["status"] == "trial"

    @pytest.mark.asyncio
    async def test_subscription_nao_expoe_stripe_ids(self):
        """GET /subscription → stripe_customer_id e stripe_subscription_id ausentes da resposta."""
        setup_auth()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/billing/subscription",
                headers=auth_headers(),
            )

        data = response.json()
        assert "stripe_customer_id" not in data
        assert "stripe_subscription_id" not in data


# ---------------------------------------------------------------------------
# TestPortalEndpoint — POST /api/v1/billing/portal
# ---------------------------------------------------------------------------


class TestPortalEndpoint:
    @pytest.mark.asyncio
    async def test_portal_com_customer_id_retorna_url(self):
        """POST /portal com stripe_customer_id → 200 com portal_url."""
        setup_auth(stripe_customer_id="cus_test_123")

        portal_url = "https://billing.stripe.com/p/session/test_abc"

        with patch(
            "app.services.billing.stripe_service.stripe.billing_portal.Session.create"
        ) as mock_create:
            mock_create.return_value = MagicMock(url=portal_url)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/billing/portal",
                    headers=auth_headers(),
                )

        assert response.status_code == 200
        data = response.json()
        assert data["portal_url"] == portal_url

    @pytest.mark.asyncio
    async def test_portal_sem_customer_id_retorna_400(self):
        """POST /portal sem stripe_customer_id → 400 com mensagem clara."""
        setup_auth(stripe_customer_id=None)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/billing/portal",
                headers=auth_headers(),
            )

        assert response.status_code == 400
        data = response.json()
        assert "checkout" in data["detail"].lower() or "assinatura" in data["detail"].lower()


# ---------------------------------------------------------------------------
# TestWebhookHandlers — handlers internos (integração com banco mockado)
# ---------------------------------------------------------------------------


class TestWebhookHandlers:
    @pytest.mark.asyncio
    async def test_handle_checkout_completed_atualiza_tenant(self):
        """checkout.session.completed → Tenant.status=active, plan e subscription_id atualizados."""
        from app.services.billing.webhook_handler import handle_checkout_completed

        tenant_id = uuid.uuid4()
        mock_tenant = make_mock_tenant(
            plan="essencial",
            status="trial",
            tenant_id=tenant_id,
            stripe_subscription_id=None,
        )

        event_data = {
            "object": {
                "metadata": {
                    "tenant_id": str(tenant_id),
                    "plan": "profissional",
                },
                "subscription": "sub_novo_789",
            }
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        await handle_checkout_completed(event_data, mock_db)

        assert mock_tenant.status == "active"
        assert mock_tenant.plan == "profissional"
        assert mock_tenant.stripe_subscription_id == "sub_novo_789"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted_cancela_tenant(self):
        """customer.subscription.deleted → Tenant.status=cancelled, subscription_id=None."""
        from app.services.billing.webhook_handler import handle_subscription_deleted

        tenant_id = uuid.uuid4()
        mock_tenant = make_mock_tenant(
            status="active",
            tenant_id=tenant_id,
            stripe_subscription_id="sub_existente",
        )

        event_data = {
            "object": {
                "metadata": {"tenant_id": str(tenant_id)},
            }
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        await handle_subscription_deleted(event_data, mock_db)

        assert mock_tenant.status == "cancelled"
        assert mock_tenant.stripe_subscription_id is None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_subscription_updated_past_due_suspende(self):
        """customer.subscription.updated com status past_due → Tenant.status=suspended."""
        from app.services.billing.webhook_handler import handle_subscription_updated

        tenant_id = uuid.uuid4()
        mock_tenant = make_mock_tenant(status="active", tenant_id=tenant_id)

        event_data = {
            "object": {
                "metadata": {"tenant_id": str(tenant_id)},
                "status": "past_due",
                "items": {"data": []},
            }
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        await handle_subscription_updated(event_data, mock_db)

        assert mock_tenant.status == "suspended"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_tenant_inexistente_nao_levanta(self):
        """checkout.session.completed com tenant_id inválido → não levanta exceção, apenas loga."""
        from app.services.billing.webhook_handler import handle_checkout_completed

        event_data = {
            "object": {
                "metadata": {
                    "tenant_id": str(uuid.uuid4()),  # tenant que não existe
                    "plan": "essencial",
                },
                "subscription": "sub_xyz",
            }
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # não encontrado
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Não deve levantar exceção
        await handle_checkout_completed(event_data, mock_db)

        # commit não deve ter sido chamado
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_evento_nao_mapeado_e_ignorado(self):
        """dispatch_webhook_event com evento desconhecido → não levanta, não chama handlers."""
        from app.services.billing.webhook_handler import dispatch_webhook_event

        event = MagicMock()
        event.type = "payment_intent.succeeded"  # não mapeado
        event.data = {"object": {}}

        mock_db = AsyncMock()

        # Não deve levantar exceção
        await dispatch_webhook_event(event, mock_db)


# ---------------------------------------------------------------------------
# TestStripeService — funções do stripe_service
# ---------------------------------------------------------------------------


class TestStripeService:
    def test_get_price_id_plano_valido(self):
        """get_price_id com plano válido → retorna price_id configurado."""
        from app.services.billing.stripe_service import get_price_id

        result = get_price_id("essencial")
        assert result == "price_essencial_placeholder"  # valor do .env de dev

    def test_get_price_id_plano_invalido_levanta_value_error(self):
        """get_price_id com plano inválido → ValueError."""
        from app.services.billing.stripe_service import get_price_id

        with pytest.raises(ValueError, match="inválido"):
            get_price_id("plano_que_nao_existe")

    @pytest.mark.asyncio
    async def test_create_stripe_customer_retorna_id(self):
        """create_stripe_customer → retorna customer.id do Stripe."""
        from app.services.billing.stripe_service import create_stripe_customer

        with patch(
            "app.services.billing.stripe_service.stripe.Customer.create"
        ) as mock_create:
            mock_create.return_value = MagicMock(id="cus_novo_abc")

            result = await create_stripe_customer(
                tenant_id=str(uuid.uuid4()),
                email="test@empresa.com",
                razao_social="Empresa Teste Ltda",
                cnpj="12345678000195",
            )

        assert result == "cus_novo_abc"

    @pytest.mark.asyncio
    async def test_create_stripe_customer_authentication_error_retorna_503(self):
        """create_stripe_customer com AuthenticationError → HTTPException 503."""
        import stripe as stripe_lib

        from app.services.billing.stripe_service import create_stripe_customer

        with patch(
            "app.services.billing.stripe_service.stripe.Customer.create",
            side_effect=stripe_lib.error.AuthenticationError("Invalid API key"),
        ):
            with pytest.raises(Exception) as exc_info:
                await create_stripe_customer(
                    tenant_id=str(uuid.uuid4()),
                    email="test@empresa.com",
                    razao_social="Empresa Teste Ltda",
                    cnpj="12345678000195",
                )

        # HTTPException com status_code 503
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_create_checkout_session_plano_invalido_retorna_400(self):
        """create_checkout_session com plano inválido → HTTPException 400."""
        from app.services.billing.stripe_service import create_checkout_session

        with pytest.raises(Exception) as exc_info:
            await create_checkout_session(
                customer_id="cus_test",
                plan="plano_invalido",
                tenant_id=str(uuid.uuid4()),
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_create_checkout_session_retorna_url(self):
        """create_checkout_session com dados válidos → retorna URL do checkout."""
        from app.services.billing.stripe_service import create_checkout_session

        expected_url = "https://checkout.stripe.com/pay/cs_test_123"

        with patch(
            "app.services.billing.stripe_service.stripe.checkout.Session.create"
        ) as mock_create:
            mock_create.return_value = MagicMock(url=expected_url)

            result = await create_checkout_session(
                customer_id="cus_test_abc",
                plan="essencial",
                tenant_id=str(uuid.uuid4()),
            )

        assert result == expected_url
