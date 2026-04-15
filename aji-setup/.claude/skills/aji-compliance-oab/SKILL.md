---
name: aji-compliance-oab
description: |
  Verifica conformidade do AJI com a Lei 8.906/94 (Estatuto da OAB). Use SEMPRE antes
  de fazer deploy de features que envolvam respostas da IA, textos de marketing, ou
  documentos gerados. Também varre termos proibidos e verifica guardrails. Essencial
  para proteger o produto de ser enquadrado como exercício ilegal da advocacia.
---

## O risco

A OAB pode obter liminar para suspender atividades do AJI se ele for caracterizado como
"consultoria jurídica" (privativa de advogado — art. 1º Lei 8.906/94).
Multa: R$ 1.000–10.000 por ato praticado.

## Scan de termos proibidos

Execute em TODO texto do produto (UI, emails, docs, código):

```bash
# Varre todo o projeto
grep -r "consultoria jurídica\|assessoria jurídica\|parecer jurídico\
\|substitui o advogado\|seu advogado\|advogado 24" \
  --include="*.tsx" --include="*.ts" --include="*.py" \
  --include="*.md" --include="*.html" .
```

Se encontrar: substituir pelos termos seguros abaixo.

## Termos seguros (use sempre)
| Proibido | Seguro |
|---------|--------|
| consultoria jurídica | orientação jurídica preventiva |
| assessoria jurídica | apoio em decisões jurídicas |
| seu advogado digital | seu guia jurídico empresarial |
| substitui o advogado | complementa o advogado |
| garantimos resultado | orientamos o procedimento |

## Checklist pré-deploy
- [ ] Termos proibidos: nenhuma ocorrência
- [ ] Disclaimer em toda resposta da IA
- [ ] Julio (OAB) listado como responsável técnico nos termos de uso
- [ ] Escalada para advogado configurada nos casos corretos
- [ ] Nenhuma resposta garante resultado
- [ ] CDC art. 42 respeitado no módulo de cobrança
