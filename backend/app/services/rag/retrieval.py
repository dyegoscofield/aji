"""
Serviço de retrieval semântico para o RAG jurídico.

Implementado diretamente com SQLAlchemy + pgvector — sem LangChain —
para ter controle total sobre os filtros de multi-tenancy (ADR-004).

Regra crítica: toda busca DEVE filtrar por
    (tenant_id IS NULL OR tenant_id = :tenant_id)
para nunca retornar chunks de outro tenant.

Configuração (ADR baseada em retrieval-search.md):
    TOP_K = 5      (padrão)
    MIN_SCORE = 0.7 (threshold mínimo de similaridade cosine)
"""

import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.embeddings import get_embedding

logger = logging.getLogger(__name__)

TOP_K_DEFAULT = 5
MIN_SCORE_DEFAULT = 0.7
CONTEXT_MAX_CHARS = 3000


async def search_similar_chunks(
    query: str,
    db: AsyncSession,
    tenant_id: uuid.UUID | None = None,
    top_k: int = TOP_K_DEFAULT,
    min_score: float = MIN_SCORE_DEFAULT,
) -> list[dict]:
    """
    Busca chunks relevantes para a query usando cosine similarity no pgvector.

    Busca em duas camadas (ADR-008):
    1. Chunks globais (tenant_id IS NULL) — base de leis, CLT, CDC, fluxos padrão
    2. Chunks do tenant específico (tenant_id = :tenant_id) — base privada

    Args:
        query:      Texto da pergunta do usuário.
        db:         Sessão assíncrona do banco de dados.
        tenant_id:  UUID do tenant autenticado. Nunca omitir em produção.
        top_k:      Número máximo de chunks retornados.
        min_score:  Threshold mínimo de similaridade (0.0 a 1.0).
                    Abaixo disso, o chunk não é relevante.

    Returns:
        Lista de dicts: {content, source_file, score, metadata, chunk_index}
        Ordenada por score descendente.

    Raises:
        RuntimeError: Se a geração de embedding falhar.
    """
    query_embedding = await get_embedding(query)

    # Converte para string no formato pgvector: [0.1, 0.2, ...]
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # Busca com cosine similarity: operador <=> retorna distância (0=idêntico, 2=oposto)
    # similarity = 1 - distância_cosine
    #
    # Multi-tenancy: retorna chunks globais OU do tenant específico.
    # NUNCA retorna chunks de outros tenants.
    sql = text(
        """
        SELECT
            id,
            content,
            source_file,
            chunk_index,
            metadata,
            tenant_id,
            1 - (embedding <=> CAST(:embedding AS vector)) AS score
        FROM legal_chunks
        WHERE
            (tenant_id IS NULL OR tenant_id = :tenant_id)
            AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :min_score
        ORDER BY score DESC
        LIMIT :top_k
        """
    )

    result = await db.execute(
        sql,
        {
            "embedding": embedding_str,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "min_score": min_score,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()

    chunks = [
        {
            "id": str(row.id),
            "content": row.content,
            "source_file": row.source_file,
            "chunk_index": row.chunk_index,
            "score": round(float(row.score), 4),
            "metadata": row.metadata or {},
            "tenant_id": str(row.tenant_id) if row.tenant_id else None,
        }
        for row in rows
    ]

    if not chunks:
        logger.info(
            "Nenhum chunk com score >= %.2f encontrado para query: %.80s...",
            min_score,
            query,
        )
    else:
        logger.debug(
            "%d chunks recuperados (top score=%.4f) para query: %.80s...",
            len(chunks),
            chunks[0]["score"],
            query,
        )

    return chunks


def assemble_context(
    chunks: list[dict],
    max_chars: int = CONTEXT_MAX_CHARS,
) -> str:
    """
    Monta o contexto para o prompt do LLM a partir dos chunks recuperados.

    Estratégia:
    - Ordena por score descendente (já vem ordenado, mas garante)
    - Concatena chunks até max_chars
    - Adiciona referência da fonte ao final de cada chunk

    Args:
        chunks:    Lista de dicts retornados por search_similar_chunks().
        max_chars: Limite total de caracteres do contexto montado.

    Returns:
        String formatada para injeção no prompt do sistema.
    """
    if not chunks:
        return ""

    sorted_chunks = sorted(chunks, key=lambda x: x["score"], reverse=True)

    parts: list[str] = []
    total_chars = 0

    for chunk in sorted_chunks:
        source = chunk.get("source_file", "fonte desconhecida")
        score = chunk.get("score", 0.0)
        content = chunk["content"].strip()

        # Referência da fonte ao final do chunk
        chunk_text = f"{content}\n[Fonte: {source} | relevância: {score:.2f}]"

        if total_chars + len(chunk_text) + 2 > max_chars:
            # Se não couber o chunk inteiro, para aqui
            remaining = max_chars - total_chars - 2
            if remaining > 100:
                # Cabe uma parte significativa — incluir truncado
                parts.append(chunk_text[:remaining] + "...")
            break

        parts.append(chunk_text)
        total_chars += len(chunk_text) + 2  # +2 para o separador \n\n

    return "\n\n".join(parts)
