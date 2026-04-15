"""
Serviço de embeddings via OpenAI text-embedding-3-small (ADR-002).

Decisão tomada: text-embedding-3-small, 1536 dims — não rediscutir.
"""

import asyncio
import logging

from openai import AsyncOpenAI, APIError, AuthenticationError, RateLimitError

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536
_MAX_RETRIES = 3
_RETRY_BACKOFF_S = 1.0


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def get_embedding(text: str) -> list[float]:
    """
    Gera embedding para um texto usando text-embedding-3-small.

    Trata erros de API com retry simples (3 tentativas, backoff exponencial).
    Levanta RuntimeError se todas as tentativas falharem — o chamador deve
    converter em HTTPException(503) quando apropriado.
    """
    client = _get_client()
    text = text.replace("\n", " ").strip()

    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = await client.embeddings.create(
                input=text,
                model=EMBEDDING_MODEL,
            )
            return response.data[0].embedding

        except AuthenticationError as exc:
            # Chave inválida — retry não resolve, falhar imediatamente
            logger.error(
                "OPENAI_API_KEY inválida ou não configurada. "
                "Configure a variável de ambiente antes de usar embeddings. "
                "Erro: %s",
                exc,
            )
            raise RuntimeError(
                "OPENAI_API_KEY inválida. Verifique a configuração."
            ) from exc

        except RateLimitError as exc:
            logger.warning(
                "Rate limit OpenAI na tentativa %d/%d. Aguardando %.1fs.",
                attempt,
                _MAX_RETRIES,
                _RETRY_BACKOFF_S * attempt,
            )
            last_error = exc
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_BACKOFF_S * attempt)

        except APIError as exc:
            logger.warning(
                "Erro de API OpenAI na tentativa %d/%d: %s",
                attempt,
                _MAX_RETRIES,
                exc,
            )
            last_error = exc
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_BACKOFF_S * attempt)

    raise RuntimeError(
        f"Falha ao gerar embedding após {_MAX_RETRIES} tentativas."
    ) from last_error


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Gera embeddings para uma lista de textos em uma única chamada de API.
    Mais eficiente que chamar get_embedding() individualmente.
    Limita a 100 textos por chamada (limite OpenAI).
    """
    if not texts:
        return []

    client = _get_client()
    cleaned = [t.replace("\n", " ").strip() for t in texts]

    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = await client.embeddings.create(
                input=cleaned,
                model=EMBEDDING_MODEL,
            )
            # A API retorna na mesma ordem dos inputs
            return [item.embedding for item in response.data]

        except AuthenticationError as exc:
            logger.error(
                "OPENAI_API_KEY inválida. Erro: %s", exc
            )
            raise RuntimeError(
                "OPENAI_API_KEY inválida. Verifique a configuração."
            ) from exc

        except (RateLimitError, APIError) as exc:
            logger.warning(
                "Erro de API OpenAI (batch) na tentativa %d/%d: %s",
                attempt,
                _MAX_RETRIES,
                exc,
            )
            last_error = exc
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_BACKOFF_S * attempt)

    raise RuntimeError(
        f"Falha ao gerar embeddings em batch após {_MAX_RETRIES} tentativas."
    ) from last_error
