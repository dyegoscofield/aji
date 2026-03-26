# Docker e Ambiente Local

## Ambientes

```
development  → localhost (docker-compose)
staging      → Railway (branch: develop)
production   → Railway (branch: main) + Vercel
```

## Docker Compose (Desenvolvimento Local)

```yaml
version: '3.9'

services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://aji:aji@db:5432/aji_dev
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
    volumes:
      - ./backend:/app
    depends_on: [db, redis]
    command: uvicorn app.main:app --reload --host 0.0.0.0

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://aji:aji@db:5432/aji_dev
      - REDIS_URL=redis://redis:6379/0
    depends_on: [db, redis]

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: aji_dev
      POSTGRES_USER: aji
      POSTGRES_PASSWORD: aji
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./infra/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

volumes:
  pgdata:
```

## Init SQL (pgvector)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

## Dockerfile Backend

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev
COPY . .
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s CMD curl -f http://localhost:8000/health || exit 1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```
