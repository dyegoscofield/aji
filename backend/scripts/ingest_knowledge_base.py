#!/usr/bin/env python3
"""
Script de ingestão da base de conhecimento global do AJI.

Percorre todos os arquivos .md em knowledge_base/ e os ingere no pgvector
como base global (tenant_id=None), disponível para todos os tenants.

Uso (dentro do container api):
    python scripts/ingest_knowledge_base.py

Ou via docker compose:
    docker compose exec api python scripts/ingest_knowledge_base.py

Requer:
    - OPENAI_API_KEY válida no .env
    - PostgreSQL com pgvector rodando e migrations aplicadas
"""

import asyncio
import logging
import sys
from pathlib import Path

# Adiciona o diretório backend ao path para importar app.*
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingest")


async def main() -> None:
    # Imports dentro do main para garantir que o sys.path está configurado
    from app.core.database import AsyncSessionLocal
    from app.services.rag.ingestion import ingest_directory

    # Resolve o diretório knowledge_base/ relativo à raiz do projeto
    # Estrutura: aji/backend/scripts/ingest_knowledge_base.py
    #            aji/knowledge_base/
    backend_dir = Path(__file__).parent.parent
    project_root = backend_dir.parent
    kb_dir = project_root / "knowledge_base"

    if not kb_dir.exists():
        logger.error(
            "Diretório knowledge_base/ não encontrado em: %s\n"
            "Crie a pasta e adicione os arquivos Markdown antes de executar.",
            kb_dir,
        )
        sys.exit(1)

    md_files = list(kb_dir.rglob("*.md"))
    if not md_files:
        logger.warning(
            "Nenhum arquivo .md encontrado em %s. "
            "Adicione documentos Markdown antes de executar.",
            kb_dir,
        )
        sys.exit(0)

    logger.info(
        "Iniciando ingestão da base de conhecimento global"
    )
    logger.info("Diretório: %s", kb_dir)
    logger.info("Arquivos encontrados: %d", len(md_files))
    for f in md_files:
        logger.info("  - %s", f.relative_to(project_root))

    async with AsyncSessionLocal() as db:
        try:
            result = await ingest_directory(
                directory=str(kb_dir),
                db=db,
                tenant_id=None,  # base global — disponível para todos
            )
        except RuntimeError as exc:
            # RuntimeError de embedding = problema com OPENAI_API_KEY
            logger.error(
                "Falha na ingestão: %s\n"
                "Verifique se OPENAI_API_KEY está configurada corretamente no .env",
                exc,
            )
            sys.exit(1)
        except Exception as exc:
            logger.error("Erro inesperado durante a ingestão: %s", exc, exc_info=True)
            sys.exit(1)

    print("\n" + "=" * 60)
    print("RESULTADO DA INGESTÃO")
    print("=" * 60)
    print(f"  Arquivos processados: {result['files_processed']}")
    print(f"  Chunks inseridos:     {result['chunks_total']}")
    print(f"  Erros:                {len(result['errors'])}")

    if result["errors"]:
        print("\nERROS:")
        for error in result["errors"]:
            print(f"  [{error['file']}] {error['error']}")

    print("=" * 60)

    if result["files_processed"] == 0:
        logger.error("Nenhum arquivo foi processado com sucesso.")
        sys.exit(1)

    logger.info("Ingestão concluída com sucesso.")


if __name__ == "__main__":
    asyncio.run(main())
