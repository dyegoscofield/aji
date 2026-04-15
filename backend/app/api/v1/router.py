from fastapi import APIRouter

from app.api.v1 import auth, billing, chat, documents, partners

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth.router)
v1_router.include_router(chat.router)
v1_router.include_router(documents.router)
v1_router.include_router(billing.router)
v1_router.include_router(partners.router)
