# Backlog e Escopo do MVP

## Status do Produto

```
Fase atual:  PRÉ-MVP
Objetivo:    Validar disposição a pagar com primeiros 10 clientes pagantes
Prazo:       90 dias para MVP funcional
Time:        Dyego (dev/infra), [dev2] (dev/infra), Julio (advogado/jurídico)
```

## O que ENTRA no MVP

```
✅ Cadastro com CNPJ (validação automática)
✅ Chat web com RAG jurídico (trabalhista + contratos)
✅ 3 planos de assinatura (Essencial/Profissional/Personalizado)
✅ Trial de 7 dias (sem cartão)
✅ Cobrança Stripe (assinatura mensal)
✅ Licença por CNPJ + limite de usuários por plano
✅ Link de indicação para contadores (rastreamento simples)
✅ Histórico de conversas
✅ 20-30 fluxos jurídicos na base de conhecimento
```

## O que FICA DE FORA do MVP

```
❌ WhatsApp (fase 2 — após validar web)
❌ Portal do parceiro contador (planilha + PIX no MVP)
❌ Personalização por empresa (plano Personal
izado: fase 2)
❌ Upload de documentos da empresa
❌ Relatórios avançados
❌ App mobile
❌ Multi-idioma
❌ Integração com sistemas de contabilidade
```

## Backlog Priorizado

### P0 — Sem isso não lança

```
[ ] Setup inicial do projeto (estrutura, DB, CI/CD)
[ ] Autenticação (cadastro CNPJ + login)
[ ] Sistema de assinaturas Stripe
[ ] Pipeline RAG básico (20 documentos jurídicos)
[ ] Interface de chat funcional
[ ] Controle de quota por plano
[ ] Trial automático de 7 dias
```

### P1 — Lança, melhora depois

```
[ ] Email de boas-vindas + onboarding
[ ] Histórico de conversas
[ ] Rastreamento de indicação (referral_code)
[ ] Modelo de advertência (geração de doc)
[ ] FAQ embutido no chat
[ ] Página de upgrade de plano
```

### P2 — Próxima versão

```
[ ] Portal do parceiro contador
[ ] WhatsApp Business
[ ] Escalada para advogado (notificação para o Julio)
[ ] Upload de documentos da empresa
[ ] Relatório mensal de uso
[ ] App mobile (React Native)
```

## Framework de Decisão para Novas Features

Antes de adicionar qualquer coisa, perguntar:
1. **Quem pede?** Vários usuários ou um barulhento?
2. **Aumenta retenção ou aquisição?** Priorizar retenção no MVP
3. **Resolve dor core** (orientação jurídica) ou é nice-to-have?
4. **Quanto tempo leva?** Se > 1 semana, vale o trade-off?
5. **Tem impacto no compliance OAB?** Se sim, consultar aji-legal primeiro

## Decisões de Produto Já Tomadas

```
✅ Licença por CNPJ (não CPF) — contexto empresarial
✅ Canal de contadores com comissão recorrente (20%)
✅ Modelo híbrido: IA + advogado para casos complexos
✅ Advogado responsável técnico (Julio) — exigência OAB
✅ Trial de 7 dias sem cartão
✅ Preços: R$197 / R$297 / R$397
✅ WhatsApp como canal secundário (web primeiro)
```
