import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    OPENAI_API_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ESSENCIAL: str = ""
    STRIPE_PRICE_PROFISSIONAL: str = ""
    STRIPE_PRICE_PERSONALIZADO: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    BRASIL_API_URL: str = "https://brasilapi.com.br/api"

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    # Armazenado como str para compatibilidade máxima com env vars
    # Use a propriedade `allowed_origins` para obter a lista parseada
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    SENTRY_DSN: str = ""

    @property
    def allowed_origins(self) -> List[str]:
        """Retorna ALLOWED_ORIGINS como lista, aceitando JSON array ou CSV."""
        value = self.ALLOWED_ORIGINS.strip()
        if value.startswith("["):
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]


settings = Settings()
