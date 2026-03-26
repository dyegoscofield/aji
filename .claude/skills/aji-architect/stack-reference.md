# Stack Tecnológica e Estrutura do Projeto AJI

## Stack Definida

```
Backend:     FastAPI (Python 3.11+)
ORM:         SQLAlchemy 2.0 + Alembic (migrations)
Banco:       PostgreSQL 16 (principal) + pgvector (embeddings RAG)
Cache:       Redis (sessões, rate limiting, filas)
IA:          OpenAI API (gpt-4o / gpt-4o-mini) + Embeddings
RAG:         LangChain ou LlamaIndex + pgvector
WhatsApp:    Evolution API (open source) ou Twilio
Auth:        JWT + validação CNPJ via Receita Federal API
Pagamentos:  Stripe (assinaturas recorrentes)
Frontend:    Next.js 14 (App Router) + Tailwind CSS
Deploy MVP:  Railway (backend) + Vercel (frontend)
Deploy Prod: AWS ECS + RDS + ElastiCache
Monit:       Sentry + PostHog
```

## Estrutura de Pastas

```
aji/
├── backend/
│   ├── app/
│   │   ├── api/           # Routers FastAPI
│   │   │   └── v1/        # auth, chat, documents, billing, partners
│   │   ├── core/          # Config, security, deps
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   │   ├── rag/       # RAG pipeline
│   │   │   ├── ai/        # OpenAI integration
│   │   │   ├── cnpj/      # CNPJ validation
│   │   │   └── billing/   # Stripe integration
│   │   ├── workers/       # Background tasks (Celery)
│   │   └── main.py
│   ├── alembic/           # Migrations
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── app/               # Next.js App Router
│   ├── components/
│   └── lib/
├── infra/
│   ├── docker-compose.yml
│   ├── railway.toml
│   └── terraform/         # Prod AWS
└── .claude/               # Agentes e skills
```

## Princípios Arquiteturais

1. **Multi-tenancy por CNPJ:** Toda query deve ter `tenant_id` — nunca retornar dados cross-tenant
2. **Isolamento de contexto:** O RAG de cada tenant usa apenas sua knowledge base
3. **Rate limiting por plano:** Essencial=30 consultas/mês, Profissional=ilimitado
4. **Auditoria completa:** Toda mensagem logada com tokens, modelo e fontes RAG
5. **Zero trust no WhatsApp:** Validar sempre se o número está associado a um tenant ativo
6. **Secrets nunca no código:** Usar variáveis de ambiente com Pydantic Settings
