import uuid
import re

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    cnpj: str
    email: EmailStr
    password: str

    @field_validator("cnpj")
    @classmethod
    def cnpj_only_digits(cls, v: str) -> str:
        """Aceita '12.345.678/0001-90' ou '12345678000190' — normaliza para 14 dígitos."""
        digits = re.sub(r"\D", "", v)
        if len(digits) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")
        return digits

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        return v


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: uuid.UUID
    razao_social: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str


class UserMeResponse(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str
    is_active: bool
    razao_social: str
    plan: str
    status: str
