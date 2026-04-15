"""
Serviço de validação e consulta de CNPJ via BrasilAPI.

Regra de segurança: CNPJ nunca é logado completo — usar mask_cnpj() em todos os logs.
"""

import logging
import re

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def clean_cnpj(cnpj: str) -> str:
    """Remove formatação e retorna apenas os 14 dígitos."""
    return re.sub(r"\D", "", cnpj)


def validate_cnpj_format(cnpj: str) -> bool:
    """
    Valida os 14 dígitos pelo algoritmo módulo 11 (padrão Receita Federal).
    Rejeita sequências repetidas (ex: 00000000000000).
    """
    digits = clean_cnpj(cnpj)

    if len(digits) != 14:
        return False

    # Rejeita sequências com todos os dígitos iguais
    if len(set(digits)) == 1:
        return False

    def _calc_digit(digits_seq: str, weights: list[int]) -> int:
        total = sum(int(d) * w for d, w in zip(digits_seq, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    first_digit = _calc_digit(digits[:12], weights_1)
    second_digit = _calc_digit(digits[:13], weights_2)

    return digits[12] == str(first_digit) and digits[13] == str(second_digit)


def mask_cnpj(cnpj: str) -> str:
    """
    Retorna versão mascarada para uso em logs.
    Exemplo: '12345678000190' -> 'XX.***.***/**XX-XX'
    """
    digits = clean_cnpj(cnpj)
    if len(digits) != 14:
        return "XX.***.***/**XX-XX"
    return f"XX.***.***/**{digits[12:14]}-XX"


async def fetch_cnpj_data(cnpj: str) -> dict:
    """
    Consulta BrasilAPI para obter dados cadastrais do CNPJ.

    Levanta HTTPException(400) se:
    - CNPJ com formato inválido
    - CNPJ não encontrado na Receita Federal
    - Situação cadastral diferente de 'ATIVA'

    Levanta HTTPException(503) se a BrasilAPI estiver indisponível.
    """
    digits = clean_cnpj(cnpj)
    masked = mask_cnpj(digits)

    if not validate_cnpj_format(digits):
        logger.warning("CNPJ com formato inválido: %s", masked)
        raise HTTPException(status_code=400, detail="CNPJ inválido")

    url = f"{settings.BRASIL_API_URL}/cnpj/v1/{digits}"
    logger.info("Consultando CNPJ %s na BrasilAPI", masked)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
    except httpx.TimeoutException:
        logger.error("Timeout ao consultar CNPJ %s na BrasilAPI", masked)
        raise HTTPException(
            status_code=503,
            detail="Serviço de validação de CNPJ indisponível. Tente novamente.",
        )
    except httpx.RequestError as exc:
        logger.error("Erro de conexão ao consultar CNPJ %s: %s", masked, type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Serviço de validação de CNPJ indisponível. Tente novamente.",
        )

    if response.status_code == 404:
        logger.warning("CNPJ %s não encontrado na Receita Federal", masked)
        raise HTTPException(status_code=400, detail="CNPJ não encontrado na Receita Federal")

    if response.status_code != 200:
        logger.error(
            "BrasilAPI retornou status %s para CNPJ %s", response.status_code, masked
        )
        raise HTTPException(
            status_code=503,
            detail="Serviço de validação de CNPJ indisponível. Tente novamente.",
        )

    data = response.json()

    # A BrasilAPI retorna 'descricao_situacao_cadastral' como string (ex: "ATIVA")
    situacao = data.get("descricao_situacao_cadastral", "").upper()
    if situacao != "ATIVA":
        logger.warning(
            "CNPJ %s com situação cadastral '%s' — recusado", masked, situacao
        )
        raise HTTPException(
            status_code=400,
            detail=f"Empresa com situação cadastral '{situacao}' na Receita Federal. "
            "Somente empresas ATIVAS podem se cadastrar.",
        )

    logger.info("CNPJ %s validado com sucesso — situação: ATIVA", masked)
    return data
