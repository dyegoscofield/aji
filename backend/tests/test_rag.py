"""
Testes do pipeline RAG — chunker, ingestion e retrieval.

Estrutura:
- test_chunker_*       : testa chunk_markdown() sem I/O externo
- test_embeddings_*    : testa comportamento de erro do serviço de embeddings
- test_search_endpoint : testa o endpoint GET /api/v1/chat/search (happy path + edge cases)

Os testes de embedding e retrieval mockam a OpenAI API para não depender de chave válida.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.rag.chunker import Chunk, chunk_markdown


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MARKDOWN = """\
# Demissão por Justa Causa

A demissão por justa causa é a rescisão do contrato de trabalho por culpa exclusiva do empregado.

## Motivos que autorizam a justa causa

Conforme o art. 482 da CLT, são motivos válidos: ato de improbidade, incontinência
de conduta, negociação habitual por conta própria, condenação criminal, desídia,
embriaguez habitual ou em serviço, violação de segredo, indisciplina ou insubordinação.

## Procedimento correto

O empregador deve seguir a gradação de penalidades: advertência verbal, advertência
escrita, suspensão e, por fim, demissão por justa causa.

### Imediatidade

A demissão deve ser aplicada logo após o conhecimento da falta. A demora configura
perdão tácito e invalida a justa causa.
"""

FAKE_EMBEDDING = [0.1] * 1536


# ---------------------------------------------------------------------------
# Testes do Chunker
# ---------------------------------------------------------------------------


class TestChunker:
    def test_retorna_lista_de_chunks(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, "fluxos/demissao.md")
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_todos_os_items_sao_chunk(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, "fluxos/demissao.md")
        for item in chunks:
            assert isinstance(item, Chunk)

    def test_chunk_index_sequencial(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, "fluxos/demissao.md")
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_source_file_preservado(self):
        source = "fluxos/demissao.md"
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source)
        for chunk in chunks:
            assert chunk.source_file == source

    def test_content_nao_vazio(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, "fluxos/demissao.md")
        for chunk in chunks:
            assert chunk.content.strip() != ""

    def test_metadata_tem_campos_obrigatorios(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, "fluxos/demissao.md")
        for chunk in chunks:
            assert "doc_type" in chunk.metadata
            assert "topic" in chunk.metadata
            assert "area" in chunk.metadata

    def test_doc_type_inferido_fluxo(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, "fluxos/demissao.md")
        for chunk in chunks:
            assert chunk.metadata["doc_type"] == "fluxo"

    def test_doc_type_inferido_faq(self):
        chunks = chunk_markdown("# Pergunta\nResposta.", "faq/trabalhista.md")
        assert chunks[0].metadata["doc_type"] == "faq"

    def test_chunk_respeitam_max_chars(self):
        max_chars = 200
        chunks = chunk_markdown(SAMPLE_MARKDOWN, "fluxos/demissao.md", max_chars=max_chars)
        for chunk in chunks:
            # Tolerância de 10% para headers que são incluídos no chunk
            assert len(chunk.content) <= max_chars * 1.1 + 50

    def test_documento_sem_headers(self):
        plain = "Texto simples sem nenhum header markdown. Apenas um parágrafo."
        chunks = chunk_markdown(plain, "outros/doc.md")
        assert len(chunks) >= 1
        assert chunks[0].content.strip() != ""

    def test_documento_vazio_retorna_lista_vazia(self):
        chunks = chunk_markdown("", "outros/vazio.md")
        assert chunks == []

    def test_header_preservado_no_conteudo(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, "fluxos/demissao.md")
        # Pelo menos um chunk deve conter um header
        has_header = any("#" in c.content for c in chunks)
        assert has_header


# ---------------------------------------------------------------------------
# Testes do serviço de embeddings
# ---------------------------------------------------------------------------


class TestEmbeddingsService:
    @pytest.mark.anyio
    async def test_get_embedding_retorna_lista_de_floats(self):
        """Testa que get_embedding retorna lista de 1536 floats quando API funciona."""
        with patch(
            "app.services.rag.embeddings._get_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            # Simula resposta da OpenAI
            mock_response = AsyncMock()
            mock_response.data = [AsyncMock(embedding=FAKE_EMBEDDING)]
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            from app.services.rag.embeddings import get_embedding

            result = await get_embedding("texto de teste")

            assert isinstance(result, list)
            assert len(result) == 1536
            assert all(isinstance(x, float) for x in result)

    @pytest.mark.anyio
    async def test_get_embedding_levanta_runtime_error_em_auth_error(self):
        """Testa que AuthenticationError (API key inválida) gera RuntimeError."""
        from openai import AuthenticationError

        with patch(
            "app.services.rag.embeddings._get_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.embeddings.create = AsyncMock(
                side_effect=AuthenticationError(
                    message="Invalid API key",
                    response=AsyncMock(status_code=401),
                    body={"error": {"message": "Invalid API key"}},
                )
            )

            from app.services.rag.embeddings import get_embedding

            with pytest.raises(RuntimeError, match="OPENAI_API_KEY inválida"):
                await get_embedding("texto de teste")

    @pytest.mark.anyio
    async def test_get_embeddings_batch_retorna_lista_correta(self):
        """Testa que get_embeddings_batch retorna lista com N embeddings."""
        texts = ["texto 1", "texto 2", "texto 3"]
        fake_embeddings = [FAKE_EMBEDDING] * 3

        with patch(
            "app.services.rag.embeddings._get_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.data = [
                AsyncMock(embedding=emb) for emb in fake_embeddings
            ]
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            from app.services.rag.embeddings import get_embeddings_batch

            result = await get_embeddings_batch(texts)
            assert len(result) == 3
            assert all(len(e) == 1536 for e in result)

    @pytest.mark.anyio
    async def test_get_embeddings_batch_lista_vazia(self):
        """Testa que lista vazia retorna lista vazia sem chamar a API."""
        from app.services.rag.embeddings import get_embeddings_batch

        result = await get_embeddings_batch([])
        assert result == []


# ---------------------------------------------------------------------------
# Testes do endpoint GET /api/v1/chat/search
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    """
    Testa o endpoint /api/v1/chat/search.

    Usa dependency_overrides do FastAPI para substituir get_current_user e
    get_current_active_tenant — a forma correta de mockar dependências injetadas.
    Não depende de banco real nem de OPENAI_API_KEY.
    """

    @pytest.fixture
    def auth_headers(self):
        """Headers de autenticação — qualquer token basta, pois a dep é overrideada."""
        return {"Authorization": "Bearer fake-token"}

    @pytest.fixture(autouse=True)
    def clear_overrides(self):
        """Limpa dependency_overrides após cada teste para não vazar entre testes."""
        yield
        app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_search_sem_autenticacao_retorna_401(self):
        """Sem header de autenticação, o oauth2_scheme retorna 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/chat/search?q=justa+causa")
        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_search_query_muito_curta_retorna_422(self, auth_headers):
        """Queries com menos de 3 caracteres devem ser rejeitadas pela validação Pydantic."""
        from app.core.deps import get_current_user, get_current_active_tenant

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_user = AsyncMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.is_active = True

        mock_tenant = AsyncMock()
        mock_tenant.id = tenant_id
        mock_tenant.status = "active"

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_active_tenant] = lambda: mock_tenant

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/chat/search?q=ab",
                headers=auth_headers,
            )
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_search_retorna_503_quando_api_key_invalida(self, auth_headers):
        """Quando o embedding falha por API key inválida, retorna 503."""
        from app.core.deps import get_current_user, get_current_active_tenant

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_user = AsyncMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.is_active = True

        mock_tenant = AsyncMock()
        mock_tenant.id = tenant_id
        mock_tenant.status = "active"

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_active_tenant] = lambda: mock_tenant

        with patch(
            "app.api.v1.chat.search_similar_chunks",
            side_effect=RuntimeError("OPENAI_API_KEY inválida"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/v1/chat/search?q=como+demitir+por+justa+causa",
                    headers=auth_headers,
                )

        assert response.status_code == 503
        assert "indisponível" in response.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_search_happy_path_retorna_chunks(self, auth_headers):
        """Happy path: autenticação OK, embedding OK, banco retorna chunks."""
        from app.core.deps import get_current_user, get_current_active_tenant

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_user = AsyncMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.is_active = True

        mock_tenant = AsyncMock()
        mock_tenant.id = tenant_id
        mock_tenant.status = "active"

        fake_chunks = [
            {
                "id": str(uuid.uuid4()),
                "content": "Art. 482 da CLT — são motivos de justa causa: ato de improbidade...",
                "source_file": "fluxos/demissao_justa_causa.md",
                "chunk_index": 0,
                "score": 0.92,
                "metadata": {"doc_type": "fluxo", "topic": "Justa Causa"},
                "tenant_id": None,
            }
        ]

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_active_tenant] = lambda: mock_tenant

        with patch(
            "app.api.v1.chat.search_similar_chunks",
            return_value=fake_chunks,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/v1/chat/search?q=como+demitir+por+justa+causa",
                    headers=auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        assert len(data["chunks"]) == 1
        assert data["chunks"][0]["score"] == 0.92
        assert data["context_assembled"] != ""
        assert data["tenant_id"] == str(tenant_id)

    @pytest.mark.anyio
    async def test_search_sem_resultados_retorna_lista_vazia(self, auth_headers):
        """Edge case: query válida mas nenhum chunk acima do threshold."""
        from app.core.deps import get_current_user, get_current_active_tenant

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_user = AsyncMock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.is_active = True

        mock_tenant = AsyncMock()
        mock_tenant.id = tenant_id
        mock_tenant.status = "active"

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_active_tenant] = lambda: mock_tenant

        with patch(
            "app.api.v1.chat.search_similar_chunks",
            return_value=[],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/v1/chat/search?q=pergunta+muito+especifica+sem+cobertura",
                    headers=auth_headers,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 0
        assert data["chunks"] == []
        assert data["context_assembled"] == ""


# ---------------------------------------------------------------------------
# Testes de assemble_context
# ---------------------------------------------------------------------------


class TestAssembleContext:
    def test_retorna_string_vazia_para_lista_vazia(self):
        from app.services.rag.retrieval import assemble_context

        result = assemble_context([])
        assert result == ""

    def test_inclui_referencia_da_fonte(self):
        from app.services.rag.retrieval import assemble_context

        chunks = [
            {
                "content": "Art. 482 da CLT prevê os motivos de justa causa.",
                "source_file": "fluxos/demissao.md",
                "score": 0.9,
            }
        ]
        result = assemble_context(chunks)
        assert "fluxos/demissao.md" in result
        assert "0.9" in result

    def test_respeita_max_chars(self):
        from app.services.rag.retrieval import assemble_context

        chunks = [
            {
                "content": "A" * 500,
                "source_file": "test.md",
                "score": 0.9,
            }
            for _ in range(20)
        ]
        result = assemble_context(chunks, max_chars=1000)
        assert len(result) <= 1100  # tolerância para o separador e referência

    def test_ordena_por_score_descendente(self):
        from app.services.rag.retrieval import assemble_context

        chunks = [
            {"content": "chunk B", "source_file": "b.md", "score": 0.75},
            {"content": "chunk A", "source_file": "a.md", "score": 0.95},
        ]
        result = assemble_context(chunks)
        pos_a = result.find("chunk A")
        pos_b = result.find("chunk B")
        assert pos_a < pos_b  # A (score maior) deve aparecer antes de B
