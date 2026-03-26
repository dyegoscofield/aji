# Monitoramento e Segurança

## Variáveis de Ambiente

```bash
# backend/.env.example

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/aji_prod
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_CHAT_MODEL_FAST=gpt-4o-mini

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ESSENCIAL=price_...
STRIPE_PRICE_PROFISSIONAL=price_...
STRIPE_PRICE_PERSONALIZADO=price_...

# Auth
JWT_SECRET=<random-256-bit>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# WhatsApp (Evolution API)
EVOLUTION_API_URL=https://...
EVOLUTION_API_KEY=...

# Email (SendGrid)
SENDGRID_API_KEY=...
FROM_EMAIL=noreply@aji.com.br

# Sentry
SENTRY_DSN=https://...

# App
ENVIRONMENT=production
DEBUG=false
ALLOWED_ORIGINS=["https://aji.com.br","https://app.aji.com.br"]
```

## Monitoramento com Sentry

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=0.1,
    before_send=lambda event, hint: _scrub_sensitive(event),
)

def _scrub_sensitive(event):
    """Remove CNPJ, tokens e conteúdo de chat dos logs do Sentry"""
    if 'request' in event:
        body = event['request'].get('data', {})
        for key in ['content', 'cnpj', 'password', 'token']:
            if key in body:
                body[key] = '[REDACTED]'
    return event
```

## Backups

```bash
#!/bin/bash
# infra/scripts/backup.sh — Backup diário automático
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump $DATABASE_URL | gzip > /tmp/aji_backup_$DATE.sql.gz
aws s3 cp /tmp/aji_backup_$DATE.sql.gz s3://aji-backups/db/$DATE.sql.gz
# Reter últimos 30 dias
aws s3 ls s3://aji-backups/db/ | sort | head -n -30 | awk '{print $4}' | \
  xargs -I{} aws s3 rm s3://aji-backups/db/{}
```

## Regras de Segurança

1. **Secrets nunca no código:** Usar variáveis de ambiente via Pydantic Settings
2. **CORS restrito:** Apenas domínios de produção no ALLOWED_ORIGINS
3. **Rate limiting:** Redis-based, por IP e por tenant
4. **Health check:** `GET /health` deve retornar 200 sem autenticação
5. **PII em logs:** NUNCA logar CNPJ completo, conteúdo de chat, tokens ou bank_data
6. **Backups:** Diários, retidos por 30 dias, criptografados em trânsito
