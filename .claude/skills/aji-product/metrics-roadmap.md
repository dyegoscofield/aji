# Métricas de Sucesso e Roadmap

## North Star Metric

```python
NORTH_STAR = "Consultas jurídicas realizadas com satisfação >= 4/5"
```

## KPIs do MVP

```python
KPIs_MVP = {
    # Aquisição
    'cadastros_trial':      {'meta': 50, 'prazo': '30 dias pós-lançamento'},
    'conversao_trial_pago': {'meta': '30%', 'benchmark': 'SaaS B2B: 15-25%'},
    
    # Engajamento
    'consultas_por_tenant': {'meta': 8, 'periodo': 'mensal'},
    'retencao_30_dias':     {'meta': '70%'},
    'retencao_90_dias':     {'meta': '55%'},
    
    # Receita
    'mrr_mes_3':            {'meta': 'R$ 10.000'},
    'ticket_medio':         {'meta': 'R$ 280'},
    'churn_mensal':         {'meta': '< 5%'},
    
    # Canal de parceiros
    'contadores_ativos':    {'meta': 5, 'prazo': '60 dias'},
    'clientes_via_contador':{'meta': '40% do total'},
    
    # Qualidade
    'satisfacao_chat':      {'meta': '>= 4.2/5'},
    'escalada_advogado':    {'meta': '< 15%', 'nota': 'muito alto = IA fraca, muito baixo = descartando casos sérios'},
}
```

## Roadmap de 6 Meses

```
MÊS 1-2: MVP
  - Setup técnico completo
  - RAG jurídico básico (trabalhista + contratos)
  - Autenticação + cobrança + chat
  - Primeiros 10 clientes pagantes

MÊS 3: Validação
  - Ajuste do RAG baseado em feedback real
  - Portal básico do parceiro (ver indicações)
  - WhatsApp via Evolution API
  - 50 clientes pagantes

MÊS 4-5: Crescimento
  - Dashboard de analytics para o empresário
  - Geração de documentos (advertência, notificação)
  - Plano Personalizado (upload de docs da empresa)
  - Sistema de escalada para advogado
  - 150 clientes pagantes

MÊS 6: Escala
  - Portal completo do parceiro contador
  - API pública para integrações
  - Mobile app (React Native)
  - Parceria com 3+ associações contábeis
  - 300 clientes pagantes / MRR R$ 85k
```
