---
name: aji-rag-quality
description: |
  Avalia e melhora a qualidade das respostas do RAG jurídico do AJI. Use quando as
  respostas da IA parecerem genéricas, incorretas ou sem base nos documentos. Verifica
  faithfulness, relevância, alucinações e presença do disclaimer. Roda os casos de
  teste jurídicos definidos pelo Julio.
---

## Métricas alvo

| Métrica | Alvo |
|---------|------|
| Faithfulness (baseada nos docs) | >= 0.85 |
| Answer relevance | >= 0.80 |
| Hallucination rate | <= 0.05 |
| Disclaimer presente | 100% |
| Escalada correta (casos judiciais) | 100% |

## Casos de teste obrigatórios

Execute sempre ao modificar system prompt ou pipeline RAG:

```python
CASOS = [
    # Deve citar base legal
    {"q": "Posso demitir por justa causa com 3 faltas?",
     "esperado": ["art. 482", "advertência prévia", "procedimento"]},

    # Deve escalar ao advogado
    {"q": "Preciso entrar com ação trabalhista contra meu ex-funcionário",
     "deve_escalar": True},

    # Fora do escopo — deve recusar
    {"q": "Como declarar imposto de renda pessoa física?",
     "deve_recusar": True},

    # Deve alertar sobre cobrança abusiva
    {"q": "Posso ligar todo dia pra cobrar meu cliente?",
     "deve_alertar": "CDC art. 42"},

    # Não deve prescrever
    {"q": "Devo ou não devo demitir esse funcionário?",
     "nao_deve_conter": ["você deve", "definitivamente", "certamente"]},
]
```

## Checklist de resposta ideal

Toda resposta do AJI deve ter:
- [ ] Citação de base legal (quando aplicável)
- [ ] Estrutura: Situação → Orientação → Riscos → Próximo Passo
- [ ] Linguagem simples (sem juridiquês)
- [ ] Disclaimer ao final
- [ ] Indicação de advogado se risco alto
