# Autenticação & Licenciamento por CNPJ

## Fluxo de Cadastro

```python
# app/api/v1/auth.py

from fastapi import APIRouter, Depends, HTTPException
from app.services.cnpj import CNPJValidator
from app.services.billing import StripeService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(data: RegisterSchema, db: AsyncSession = Depends(get_db)):
    """
    Fluxo de cadastro:
    1. Validar CNPJ na Receita Federal
    2. Verificar se CNPJ já existe
    3. Criar tenant + owner user
    4. Criar customer no Stripe
    5. Iniciar trial de 7 dias
    6. Enviar email de boas-vindas
    """
    # Validar CNPJ
    cnpj_data = await CNPJValidator.validate(data.cnpj)
    if not cnpj_data.is_valid or cnpj_data.status != "ATIVA":
        raise HTTPException(400, "CNPJ inválido ou empresa inativa na Receita Federal")
    
    # Verificar duplicata
    existing = await TenantRepository.get_by_cnpj(db, data.cnpj)
    if existing:
        raise HTTPException(409, "CNPJ já cadastrado")
    
    # Criar tenant
    tenant = await TenantRepository.create(db, {
        "cnpj": data.cnpj,
        "razao_social": cnpj_data.razao_social,
        "plan": "profissional",
        "status": "trial",
        "trial_ends_at": datetime.utcnow() + timedelta(days=7),
        "partner_id": data.referral_code and await PartnerRepository.get_by_code(db, data.referral_code)
    })
    
    # Stripe
    customer = await StripeService.create_customer(tenant)
    await TenantRepository.update(db, tenant.id, {"stripe_customer_id": customer.id})
    
    return {"tenant_id": str(tenant.id), "access_token": create_jwt(tenant)}
```

## Validação de CNPJ

```python
# app/services/cnpj.py

import httpx
from functools import lru_cache

class CNPJValidator:
    BASE_URL = "https://brasilapi.com.br/api/cnpj/v1"
    
    @staticmethod
    async def validate(cnpj: str) -> CNPJData:
        """
        Usa BrasilAPI (gratuita, sem autenticação).
        Fallback: ReceitaWS
        """
        cnpj_clean = re.sub(r'\D', '', cnpj)
        
        if len(cnpj_clean) != 14:
            return CNPJData(is_valid=False)
        
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{cls.BASE_URL}/{cnpj_clean}")
                if resp.status_code == 200:
                    data = resp.json()
                    return CNPJData(
                        is_valid=True,
                        cnpj=cnpj_clean,
                        razao_social=data['razao_social'],
                        nome_fantasia=data.get('nome_fantasia'),
                        status=data['descricao_situacao_cadastral'],
                        atividade_principal=data['cnae_fiscal_descricao'],
                        uf=data['uf'],
                        municipio=data['municipio'],
                    )
            except Exception:
                return CNPJData(is_valid=False, error="API indisponível")
        
        return CNPJData(is_valid=False)
```

## Regras Críticas

1. **Toda query DEVE incluir `tenant_id`** — ver CLAUDE.md seção 16
2. CNPJ é o identificador primário do tenant, não o email
3. JWT stateless — sem sessão no servidor
4. Trial de 7 dias sem cartão de crédito
