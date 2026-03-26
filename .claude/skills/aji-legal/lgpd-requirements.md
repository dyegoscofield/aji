# LGPD — Requisitos para o AJI

## Configuração

```python
LGPD_REQUIREMENTS = {
    'base_legal': 'Execução de contrato (art. 7º, V) + legítimo interesse',
    
    'dados_sensiveis': [
        # O AJI PODE coletar dados sobre:
        # Relações trabalhistas, contratos, inadimplência
        # ATENÇÃO: dados de saúde, religião, origem racial NÃO
    ],
    
    'retencao': {
        'mensagens_chat': '5 anos (prazo prescricional trabalhista)',
        'dados_empresa': 'Enquanto ativo + 5 anos após cancelamento',
        'logs_acesso': '6 meses',
    },
    
    'direitos_titulares': [
        'Acesso aos dados: endpoint GET /api/v1/me/data',
        'Portabilidade: export JSON/CSV dos dados',
        'Eliminação: DELETE /api/v1/me (anonimiza, não apaga logs)',
        'Correção: PATCH /api/v1/me',
    ],
    
    'dpo': 'Designar DPO quando base de usuários > 500 tenants'
}
```

## Regras

1. **Dados sensíveis NUNCA em logs:** CNPJ completo, bank_data, dados pessoais de funcionários do tenant
2. **Retenção:** Respeitar prazos prescricionais trabalhistas (5 anos)
3. **Portabilidade:** Endpoint de export DEVE existir antes do lançamento
4. **Anonimização:** DELETE não apaga — anonimiza (mantém logs sem PII)
5. **DPO:** Obrigatório a partir de 500 tenants ativos
