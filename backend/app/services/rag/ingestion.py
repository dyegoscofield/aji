"""
Serviço de ingestão de documentos jurídicos no pgvector.

Fluxo:
    Arquivo Markdown → chunk_markdown() → get_embeddings_batch() → upsert legal_chunks

Regra de multi-tenancy:
    tenant_id=None  → base global (compartilhada com todos os tenants)
    tenant_id=UUID  → base privada (plano Personalizado — fase 2)
"""

import logging
import uuid
from pathlib import Path

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_chunk import LegalChunk
from app.services.rag.chunker import chunk_markdown
from app.services.rag.embeddings import get_embeddings_batch

logger = logging.getLogger(__name__)

# Tamanho do lote para chamadas de embedding (limite OpenAI: 2048 inputs)
_EMBED_BATCH_SIZE = 50


async def ingest_file(
    file_path: str,
    db: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> int:
    """
    Ingere um arquivo Markdown na tabela legal_chunks.

    Estratégia de upsert: remove todos os chunks existentes do mesmo
    source_file + tenant_id antes de reinserir. Isso garante consistência
    quando o documento é atualizado.

    Args:
        file_path:  Caminho absoluto do arquivo Markdown.
        db:         Sessão assíncrona do banco de dados.
        tenant_id:  None = base global; UUID = base privada do tenant.

    Returns:
        Número de chunks inseridos.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        RuntimeError:      Se a chamada de embedding falhar (API key inválida, etc.).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    content = path.read_text(encoding="utf-8")

    # Calcula source_file relativo à raiz knowledge_base/ para portabilidade
    source_file = _relative_source(file_path)

    logger.info("Iniciando ingestão: %s (tenant_id=%s)", source_file, tenant_id)

    chunks = chunk_markdown(content, source_file)
    if not chunks:
        logger.warning("Nenhum chunk gerado para %s", source_file)
        return 0

    # Remove chunks anteriores do mesmo arquivo/tenant antes do upsert
    await db.execute(
        delete(LegalChunk).where(
            LegalChunk.source_file == source_file,
            LegalChunk.tenant_id == tenant_id,
        )
    )

    # Gera embeddings em batches para não estourar o limite de tokens por chamada
    texts = [c.content for c in chunks]
    embeddings: list[list[float]] = []

    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch_texts = texts[i : i + _EMBED_BATCH_SIZE]
        batch_embeddings = await get_embeddings_batch(batch_texts)
        embeddings.extend(batch_embeddings)
        logger.debug(
            "Batch %d/%d — %d embeddings gerados",
            i // _EMBED_BATCH_SIZE + 1,
            (len(texts) + _EMBED_BATCH_SIZE - 1) // _EMBED_BATCH_SIZE,
            len(batch_embeddings),
        )

    # Persiste os chunks
    for chunk, embedding in zip(chunks, embeddings):
        legal_chunk = LegalChunk(
            content=chunk.content,
            embedding=embedding,
            source_file=source_file,
            chunk_index=chunk.chunk_index,
            tenant_id=tenant_id,
            metadata_=chunk.metadata,
        )
        db.add(legal_chunk)

    await db.commit()

    logger.info(
        "Ingestão concluída: %s — %d chunks inseridos", source_file, len(chunks)
    )
    return len(chunks)


async def ingest_directory(
    directory: str,
    db: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> dict:
    """
    Ingere todos os arquivos Markdown de um diretório recursivamente.

    Args:
        directory:  Caminho absoluto do diretório a processar.
        db:         Sessão assíncrona do banco de dados.
        tenant_id:  None = base global; UUID = base privada do tenant.

    Returns:
        Dict com {"files_processed": N, "chunks_total": M, "errors": [...]}
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Diretório não encontrado: {directory}")

    md_files = sorted(dir_path.rglob("*.md"))
    if not md_files:
        logger.warning("Nenhum arquivo .md encontrado em %s", directory)
        return {"files_processed": 0, "chunks_total": 0, "errors": []}

    files_processed = 0
    chunks_total = 0
    errors: list[dict] = []

    for md_file in md_files:
        try:
            count = await ingest_file(str(md_file), db, tenant_id)
            files_processed += 1
            chunks_total += count
        except Exception as exc:
            logger.error("Erro ao ingerir %s: %s", md_file, exc)
            errors.append({"file": str(md_file), "error": str(exc)})

    logger.info(
        "Ingestão do diretório concluída: %d arquivos, %d chunks, %d erros",
        files_processed,
        chunks_total,
        len(errors),
    )

    return {
        "files_processed": files_processed,
        "chunks_total": chunks_total,
        "errors": errors,
    }


def _relative_source(file_path: str) -> str:
    """
    Retorna o caminho relativo a partir de 'knowledge_base/' para
    garantir portabilidade entre ambientes.

    Exemplo:
        /app/knowledge_base/fluxos/demissao.md → fluxos/demissao.md
    """
    path = Path(file_path)
    parts = path.parts
    try:
        kb_index = next(
            i for i, p in enumerate(parts) if p == "knowledge_base"
        )
        return "/".join(parts[kb_index + 1 :])
    except StopIteration:
        # Se não encontrar knowledge_base no caminho, usa o nome do arquivo
        return path.name
