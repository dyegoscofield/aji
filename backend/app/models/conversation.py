"""
Model SQLAlchemy para Conversation.

Regra crítica de multi-tenancy: toda query DEVE incluir tenant_id como filtro.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Enum as SAEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.message import Message

ChannelEnum = SAEnum("web", "whatsapp", name="conversation_channel")
StatusEnum = SAEnum("active", "escalated", "closed", name="conversation_status")


class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(
        ChannelEnum,
        nullable=False,
        default="web",
    )
    status: Mapped[str] = mapped_column(
        StatusEnum,
        nullable=False,
        default="active",
    )
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        lazy="dynamic",
        order_by="Message.created_at",
    )
