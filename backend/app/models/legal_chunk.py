import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class LegalChunk(Base, UUIDMixin, TimestampMixin):
    """
    Chunk de documento jurídico armazenado no pgvector.

    tenant_id=NULL  → base global compartilhada (disponível para todos os tenants)
    tenant_id=UUID  → base privada do tenant (plano Personalizado — fase 2)

    Regra de multi-tenancy: toda busca DEVE filtrar por
    (tenant_id IS NULL OR tenant_id = :tenant_id)
    """

    __tablename__ = "legal_chunks"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=False)

    # Rastreabilidade
    source_file: Mapped[str] = mapped_column(String(512), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Multi-tenancy: NULL = global, UUID = privado do tenant
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # JSONB com metadados do chunk: topic, tags, doc_type, area, legal_reference, etc.
    # Usar metadata_ porque "metadata" é reservado pelo SQLAlchemy (DeclarativeBase)
    metadata_: Mapped[dict] = mapped_column(
        "metadata",  # nome real da coluna no banco
        JSONB,
        nullable=False,
        default=dict,
    )
