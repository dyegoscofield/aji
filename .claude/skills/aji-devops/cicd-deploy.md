# CI/CD e Deploy

## Railway Config

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "backend/Dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

## GitHub Actions CI/CD

```yaml
name: Deploy AJI

on:
  push:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: aji_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: Install deps
        run: cd backend && pip install poetry && poetry install
      - name: Run migrations
        run: cd backend && alembic upgrade head
        env:
          DATABASE_URL: postgresql://postgres:test@localhost/aji_test
      - name: Run tests
        run: cd backend && pytest tests/ -v --cov=app --cov-report=xml
        env:
          DATABASE_URL: postgresql://postgres:test@localhost/aji_test
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: railwayapp/railway-action@v1
        with:
          service: aji-staging
          token: ${{ secrets.RAILWAY_TOKEN }}

  deploy-production:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy Backend (Railway)
        uses: railwayapp/railway-action@v1
        with:
          service: aji-production
          token: ${{ secrets.RAILWAY_TOKEN }}
      - name: Deploy Frontend (Vercel)
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

## Checklist de Deploy em Produção

```
□ Migrations rodadas: alembic upgrade head
□ pgvector extension ativada no RDS
□ Stripe webhooks configurados no painel
□ Evolution API configurada e testada
□ Variáveis de ambiente todas definidas
□ Sentry DSN configurado
□ CORS configurado para o domínio de produção
□ Rate limiting ativado no Redis
□ Backup automático configurado no S3
□ Health check endpoint respondendo: GET /health
□ Smoke test de chat funcionando end-to-end
```
