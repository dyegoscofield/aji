# Importar todos os models para que o Alembic os detecte durante autogenerate.
# A ordem importa: Tenant deve ser importado antes de User por causa do FK,
# e Conversation/Message devem vir após Tenant e User.
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.legal_chunk import LegalChunk  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message  # noqa: F401

__all__ = ["Tenant", "User", "LegalChunk", "Conversation", "Message"]
