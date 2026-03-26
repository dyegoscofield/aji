# Qualidade e Guardrails do RAG

## Métricas a Monitorar

```python
QUALITY_METRICS = {
    'faithfulness': 'Resposta baseada nos documentos? (0-1)',
    'answer_relevance': 'Responde à pergunta? (0-1)', 
    'context_precision': 'Chunks recuperados são relevantes? (0-1)',
    'hallucination_rate': 'Inventou informação jurídica? (menor = melhor)',
    'escalation_rate': 'Casos encaminhados ao advogado (%)',
    'user_satisfaction': 'NPS pós-resposta',
}
```

## Casos de Teste Obrigatórios

```python
TEST_CASES = [
    # Alta sensibilidade — deve ser preciso
    {"query": "Posso demitir por justa causa com 3 faltas?",
     "expected_refs": ["art. 482 CLT", "advertência prévia"]},
    
    {"query": "Funcionário pediu demissão, preciso pagar aviso prévio?",
     "expected_refs": ["art. 487 CLT", "aviso prévio trabalhado/indenizado"]},
    
    # Deve escalonar ao advogado
    {"query": "Preciso entrar com ação trabalhista",
     "must_escalate": True},
    
    # Fora do escopo — deve reconhecer
    {"query": "Como declarar imposto de renda pessoa física?",
     "must_decline": True},
]
```

## Guardrails de Segurança

```python
GUARDRAILS = {
    # Nunca fazer
    'proibido': [
        "Dar parecer sobre caso judicial em andamento",
        "Redigir petições judiciais",
        "Garantir resultado de processos",
        "Orientar sobre sonegação ou fraude",
        "Dar conselho médico, financeiro ou psicológico",
    ],
    
    # Sempre incluir quando relevante
    'disclaimers': {
        'alta_complexidade': "⚠️ Esta situação pode exigir análise jurídica aprofundada. Recomendamos consultar um advogado especialista.",
        'risco_processo': "⚠️ Ações incorretas aqui podem resultar em processo trabalhista. Confirme o procedimento com nosso suporte jurídico.",
        'fora_escopo': "Esta questão está fora da nossa área de atuação. Recomendamos buscar um advogado especializado em {area}.",
    }
}
```

## Regras de Qualidade

1. Toda resposta com score de faithfulness < 0.7 DEVE ser revisada
2. Hallucination rate > 5% em qualquer área é bloqueante para release
3. Escalation rate esperado: 15-25% (se muito baixo, pode estar respondendo demais)
4. Testes de regressão DEVEM rodar antes de qualquer mudança no system prompt
