---
name: fastapi-templates
description: |
  Cria projetos FastAPI production-ready com padrões async, dependency injection e
  error handling completo. Use ao criar endpoints, services, repositories ou qualquer
  código Python backend. Garante SQLAlchemy 2.0 async, Pydantic v2, JWT, e estrutura
  de pastas consistente com o projeto AJI.
---

## Estrutura padrão AJI

```
backend/app/
├── api/v1/         # Routers (um por recurso)
├── core/           # Config, security, deps
├── models/         # SQLAlchemy 2.0
├── schemas/        # Pydantic v2
├── services/       # Business logic
├── repositories/   # Data access
└── workers/        # Celery tasks
```

## Padrões obrigatórios

```python
# Router padrão
router = APIRouter(prefix="/resource", tags=["resource"])

# Dependency injection
async def get_current_tenant(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Tenant: ...

# Response schema sempre, nunca retornar ORM direto
@router.get("/", response_model=list[ResourceSchema])
async def list_resources(tenant = Depends(get_current_tenant)):
    ...

# Erros estruturados
raise HTTPException(
    status_code=400,
    detail={"code": "VALIDATION_ERROR", "message": "..."}
)
```

## SQLAlchemy 2.0 async

```python
async with async_session() as db:
    result = await db.execute(select(Model).where(Model.tenant_id == tenant_id))
    items = result.scalars().all()
```

## Gotchas (pontos de falha comuns)
- SEMPRE usar `async def` nos endpoints
- NUNCA retornar objeto ORM — sempre serializar com schema
- SEMPRE fechar a sessão do DB (usar context manager)
- Pydantic v2: usar `model_validate()` não `from_orm()`
