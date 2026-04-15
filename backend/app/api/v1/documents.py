from fastapi import APIRouter

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/generate")
async def generate_document():
    # TODO: Semana 5-6 — geração de documentos (advertência, contrato, etc.)
    return {"message": "not implemented"}
