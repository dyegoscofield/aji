from fastapi import APIRouter

router = APIRouter(prefix="/partners", tags=["partners"])


@router.post("/register")
async def register_partner():
    # TODO: Semana 9 — cadastro de parceiro contador
    return {"message": "not implemented"}


@router.get("/{referral_code}/stats")
async def partner_stats(referral_code: str):
    # TODO: Semana 9 — estatísticas de indicação
    return {"message": "not implemented"}
