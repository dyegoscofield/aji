import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User

PlanEnum = SAEnum("essencial", "profissional", "personalizado", name="tenant_plan")
StatusEnum = SAEnum("trial", "active", "suspended", "cancelled", name="tenant_status")


def _trial_ends_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


class Tenant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"

    cnpj: Mapped[str] = mapped_column(String(14), unique=True, nullable=False, index=True)
    razao_social: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(PlanEnum, nullable=False, default="essencial")
    status: Mapped[str] = mapped_column(StatusEnum, nullable=False, default="trial")
    trial_ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_trial_ends_at,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    partner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", lazy="selectin"
    )
