# CLAUDE.md — Briefing Completo do Projeto AJI

> Este arquivo fornece todo o contexto necessário para o Claude Code trabalhar no projeto AJI sem necessidade de explicações adicionais. Leia este arquivo inteiro antes de qualquer tarefa.

---

## 0. Política de Honestidade e Conduta (OBRIGATÓRIO)

### Anti-Bajulação

Este projeto exige **honestidade radical** em todas as interações. Os agentes do AJI existem para ajudar a tomar decisões técnicas corretas, não para validar decisões ruins.

**Frases PROIBIDAS — nunca usar:**

| Proibido | Substituir por |
|----------|---------------|
| "Ótima ideia!" | "Analisei a proposta. Aqui está minha avaliação:" |
| "Excelente pergunta!" | [Responder diretamente] |
| "Perfeito!" | "Funciona. Um ponto de atenção:" |
| "Com certeza!" | "Sim, porque [justificativa técnica]" |
| "Absolutamente!" | "Correto, com base em [referência]" |
| "Boa escolha!" | "Essa abordagem tem [prós]. Considere também [contras]." |
| "Sem dúvida!" | "Concordo, dado que [embasamento]" |

**Regras de conduta:**

1. **Quando discordar:** Apresentar a alternativa com embasamento técnico ou teórico. Formato: "Entendo a proposta, mas considero [alternativa] mais adequada porque [razão]. Especificamente: [evidência]."
2. **Quando não souber:** Dizer explicitamente: "Não tenho certeza sobre isso. Preciso de mais contexto sobre [X] para dar uma orientação confiável."
3. **Quando o usuário insistir em algo errado:** Manter a posição técnica. Formato: "Respeito a decisão, mas registro que [risco/problema]. Se prosseguir, recomendo [mitigação]."
4. **Toda opinião deve ter embasamento:** Nunca afirmar sem justificativa. Citar documentação, padrões de mercado, experiência do projeto ou trade-offs concretos.

### Disclaimer de IA

Toda resposta gerada pelos agentes que contenha orientação técnica ou jurídica deve incluir, quando relevante:

> *Resposta gerada por IA. Valide com a equipe antes de aplicar em produção.*

### Princípio de Não-Ação

Os agentes **NUNCA devem executar ações que o usuário não solicitou**. Se identificar uma melhoria ou correção necessária, deve **sugerir** e aguardar aprovação antes de implementar.

---

## 1. O que é o AJI

**AJI — Assistente Jurídico Inteligente** é um SaaS de orientação jurídica com IA voltado para empresários e PMEs brasileiras (5–100 funcionários) que não possuem jurídico interno.

**Problema que resolve:** Empresários tomam decisões com impacto jurídico diariamente — demissões, contratos, cobranças, advertências — sem orientação adequada. Consultas jurídicas tradicionais são caras, demoradas e o advogado nem sempre está disponível no momento da decisão.

**Solução:** Um assistente com IA treinado com rotinas jurídicas empresariais brasileiras, disponível 24h via web, que responde dúvidas do dia a dia de forma clara e preventiva — sem substituir o advogado, mas reduzindo drasticamente os riscos de decisões sem amparo jurídico.

---

## 2. Time

| Pessoa | Papel |
|--------|-------|
| **Dyego** | Dev / Infra / Product Owner — background em Python, IA/Prompt Engineering, Cloud/DevOps e Produto |
| **[Dev 2]** | Dev / Infraestrutura |
| **Julio** | Advogado — Responsável Técnico Jurídico (OAB) — já tem toda a base jurídica estruturada |

> **Nível técnico de referência:** Dyego tem background sólido em Python backend, engenharia de prompts, cloud e produto. As decisões técnicas podem e devem ser feitas sem simplificações — ir direto ao ponto com código, arquitetura e trade-offs reais.

O Julio como advogado OAB inscrito é o **requisito regulatório mais crítico** do projeto — ele é o escudo jurídico que protege o produto de ser enquadrado como exercício ilegal da advocacia (Lei 8.906/94). Ele também já entregou o conteúdo jurídico estruturado que alimentará a base de conhecimento.

---

## 3. Interface & Canais

### Interface do usuário
**Ambos: chat livre + fluxos guiados.** O empresário terá:
- **Chat livre** (estilo ChatGPT) como interface principal — pergunta em linguagem natural, recebe orientação
- **Fluxos guiados** para situações comuns e de alto risco (ex: wizard de justa causa, checklist de advertência) — reduz erros e garante que o usuário informe o contexto correto

A combinação é estratégica: o chat é o diferencial de UX, os fluxos garantem qualidade jurídica nas situações mais críticas.

### Canais de acesso
**MVP: somente Web (navegador).** WhatsApp fica para a fase 2, após validação do produto web. Isso simplifica o MVP e reduz o risco de compliance com a Evolution API.

---

## 4. Modelo de IA — Decisão Técnica

### LLM escolhido: OpenAI — estratégia de dois modelos

**gpt-4o-mini** → 90% das consultas (perguntas simples, fluxos guiados, FAQ)
**gpt-4o** → 10% dos casos (alta complexidade, identificados automaticamente pelo sistema)

**Por que não DeepSeek:**
- Dados sensíveis (CNPJ, situações trabalhistas) passariam por servidores chineses → problema real de LGPD
- Instabilidade de API documentada → risco para produto 24h
- Menor treinamento em legislação brasileira / CLT

**Por que não Claude Anthropic como LLM principal:**
- Qualidade superior mas custo de API escala mais rápido com volume
- Pode entrar como opção futura para plano Personalizado (maior ticket)

**Por que OpenAI:**
- Melhor custo-benefício para RAG sobre base jurídica estruturada
- gpt-4o-mini com RAG bem feito responde questões jurídicas padrão com alta qualidade
- Custo estimado MVP: R$ 150–400/mês

```python
# Lógica de seleção de modelo
def select_model(query: str, complexity_score: float) -> str:
    if complexity_score > 0.75:  # caso complexo detectado pelo sistema
        return "gpt-4o"
    return "gpt-4o-mini"  # default
```

---

## 5. Base de Conhecimento Jurídico

**Status: conteúdo já existe.** O Julio já tem toda a base jurídica estruturada — fluxos de orientação preventiva, modelos de documentos, metodologia de diagnóstico.

**Tarefa técnica:** converter esse conteúdo para o formato adequado de ingestão no RAG (chunking, embedding, indexação no pgvector).

```
knowledge_base/
├── global/                          # Compartilhada com todos os tenants
│   ├── legislacao/
│   │   ├── clt_consolidada.md       # CLT completa
│   │   ├── cdc_consumidor.md
│   │   ├── lgpd_empresas.md
│   │   └── codigo_civil_contratos.md
│   ├── fluxos/                      # Conteúdo do Julio — já estruturado
│   │   ├── demissao_justa_causa.md
│   │   ├── advertencia_disciplinar.md
│   │   ├── cobranca_inadimplente.md
│   │   └── rescisao_contratual.md
│   ├── modelos/                     # Documentos prontos para geração
│   │   ├── advertencia_escrita.md
│   │   ├── contrato_prestacao_servicos.md
│   │   ├── notificacao_cobranca.md
│   │   └── termo_confidencialidade.md
│   └── faq/
│       ├── trabalhista.md
│       ├── contratos.md
│       └── lgpd.md
└── tenant_{uuid}/                   # Base privada (plano Personalizado — fase 2)
```

### Pipeline RAG

```
Conteúdo Julio (já estruturado)
         ↓
  Preprocessor + Chunker
  (por artigo/cláusula/tema)
         ↓
  Embedder (text-embedding-3-small)
         ↓
     pgvector (PostgreSQL)

  Query do usuário
         ↓
  Query Embedding → Semantic Search (cosine) → Reranker
         ↓
  Context Assembly → gpt-4o-mini (ou gpt-4o) → Resposta com disclaimer
```

---

## 6. Modelo de Negócio

### Planos SaaS (licença por CNPJ)

| Plano | Preço | Limite |
|-------|-------|--------|
| Essencial | R$ 197/mês | 30 consultas/mês, 1 usuário |
| Profissional | R$ 297/mês | Ilimitado, 3 usuários |
| Personalizado | R$ 397/mês | Ilimitado, usuários ilimitados, base jurídica da empresa |

### Canal de Parceiros — Contadores
- Escritórios de contabilidade indicam o AJI para seus clientes
- Recebem **20% de comissão recorrente** enquanto o cliente permanecer ativo
- Link exclusivo de indicação rastreável
- R$ 59,40/cliente/mês no plano Profissional
- **Este canal é prioritário para os primeiros 50 clientes** — CAC praticamente zero
- No MVP: controle via planilha + pagamento PIX (portal do parceiro fica para fase 2)

### Dois tipos de uso
1. **Plano Empresa** — licença por CNPJ, uso pelos colaboradores da empresa
2. **Plano Escritório Contador** — acesso interno com volume limitado, sem personalização por cliente (evita que contador compre uma licença e atenda toda a carteira)

---

## 7. Fase Atual & Urgência

**Status:** Pré-MVP — nenhum cliente ainda. Fase de construção.

**Prazo:** **Urgente — 60 dias para MVP funcional.**

### Cronograma real (60 dias)

```
SEMANA 1–2  │ Setup: repo, Docker, PostgreSQL+pgvector, FastAPI base, auth JWT
SEMANA 3–4  │ RAG: ingestão do conteúdo do Julio, pipeline embeddings, busca semântica
SEMANA 5–6  │ Chat: endpoint de conversa com streaming SSE, controle de quota por plano
SEMANA 7    │ Pagamentos: Stripe assinaturas, trial 7 dias, webhook
SEMANA 8    │ Frontend: Next.js — cadastro CNPJ, onboarding, interface de chat
SEMANA 9    │ Parceiros: link de indicação, rastreamento básico
SEMANA 10   │ QA, ajustes, smoke tests, deploy Railway + Vercel
```

**Decisão de escopo para caber em 60 dias:**
- ✅ Foco total em web — sem WhatsApp
- ✅ Portal do parceiro simplificado (link de indicação + planilha manual)
- ✅ RAG com base do Julio — sem upload de documentos pelo usuário ainda
- ✅ Plano Personalizado no cadastro mas base privada só na fase 2

---

## 8. Stack Tecnológica

```
Backend:     FastAPI (Python 3.11+)
ORM:         SQLAlchemy 2.0 async + Alembic (migrations)
Banco:       PostgreSQL 16 + pgvector (embeddings RAG)
Cache/Filas: Redis + Celery (background tasks)
LLM:         OpenAI API — gpt-4o-mini (default) + gpt-4o (complexo)
Embeddings:  text-embedding-3-small
RAG:         LangChain + pgvector
Auth:        JWT + validação CNPJ via BrasilAPI (gratuita)
Pagamentos:  Stripe (assinaturas recorrentes)
Frontend:    Next.js 14 (App Router) + Tailwind CSS
Estado:      Zustand + React Query
Streaming:   Server-Sent Events (SSE) para resposta em tempo real
Deploy MVP:  Railway (backend) + Vercel (frontend)
Deploy Prod: AWS ECS + RDS + ElastiCache
Monit:       Sentry + PostHog
WhatsApp:    Fase 2 — Evolution API (MVP) → Meta Business API (escala)
```

---

## 9. Arquitetura do Sistema

### Estrutura de Pastas

```
aji/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py          # cadastro CNPJ, login, JWT
│   │   │   ├── chat.py          # conversas + mensagens + streaming SSE
│   │   │   ├── documents.py     # geração de documentos (advertência, etc.)
│   │   │   ├── billing.py       # Stripe webhooks e assinaturas
│   │   │   └── partners.py      # referral link, rastreamento
│   │   ├── core/                # config, security, deps, settings
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic v2 schemas
│   │   ├── services/
│   │   │   ├── rag/             # ingestão + retrieval + reranker
│   │   │   ├── ai/              # OpenAI client, seleção de modelo
│   │   │   ├── cnpj/            # BrasilAPI integration
│   │   │   └── billing/         # Stripe service
│   │   └── workers/             # Celery tasks (ingestão, emails, relatórios)
│   ├── alembic/                 # migrations
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   │   ├── (marketing)/         # landing page pública
│   │   ├── (auth)/              # login, cadastro CNPJ, onboarding wizard
│   │   ├── (dashboard)/         # chat, histórico, configurações, plano
│   │   └── (parceiro)/          # portal básico do contador
│   └── components/
├── knowledge_base/              # conteúdo jurídico do Julio
├── infra/
│   ├── docker-compose.yml
│   └── railway.toml
└── .claude/
    └── agents/                  # sub-agents especializados
```

### Modelos de Dados Principais

```python
Tenant:       id, cnpj (unique), razao_social, plan, status,
              stripe_customer_id, stripe_subscription_id,
              partner_id (FK nullable), trial_ends_at

User:         id, tenant_id (FK), email, role (owner/admin/member),
              phone (para WhatsApp fase 2)

Conversation: id, tenant_id, user_id, channel (web/whatsapp),
              status (active/escalated/closed), topic

Message:      id, conversation_id, role (user/assistant),
              content, tokens_used, model, rag_sources (JSONB)

Partner:      id, name, email, cnpj, referral_code (unique),
              commission_rate (default 0.20), status, bank_data (JSONB encrypted)

LegalChunk:   id, content, embedding (vector 1536), metadata (JSONB),
              tenant_id (NULL = base global compartilhada)
```

---

## 10. Compliance Jurídico — CRÍTICO

O AJI opera no limite entre **informação jurídica** (permitida) e **consultoria jurídica** (privativa de advogado — Lei 8.906/94, art. 1º).

### ✅ Permitido
- Explicar o que diz a lei e descrever procedimentos gerais
- Apresentar modelos de documentos genéricos
- Orientar sobre o que pesquisar ou quem consultar
- Indicar quando consultar advogado

### ❌ Proibido
- Analisar caso específico e prescrever ação legal como conclusão definitiva
- Redigir peças processuais (petições, recursos)
- Emitir parecer jurídico formal
- Garantir resultado de qualquer ação

### Termos proibidos no produto e marketing
`consultoria jurídica` · `assessoria jurídica` · `substitui o advogado` · `seu advogado digital` · `parecer jurídico`

### Termos seguros
`orientação jurídica preventiva` · `apoio em decisões jurídicas` · `guia jurídico empresarial` · `primeiro nível de suporte jurídico`

### Regras obrigatórias no sistema
- Toda resposta do AJI inclui disclaimer indicando que não substitui advogado
- Casos de alta complexidade ou risco judicial → escalada obrigatória para o Julio
- Julio (OAB) é o responsável técnico formal — nome e OAB devem constar nos termos de uso

---

## 11. Sub-Agents Disponíveis (.claude/agents/)

| Agent | Use para |
|-------|----------|
| `aji-architect` | Decisões técnicas de alto nível, stack, modelos de dados, ADRs |
| `aji-backend` | FastAPI, endpoints, Stripe, CNPJ, SQLAlchemy, Celery, testes |
| `aji-rag` | Pipeline de IA, embeddings, prompts, system prompt, qualidade |
| `aji-frontend` | Next.js, chat UI com SSE streaming, dashboard, portal parceiro |
| `aji-devops` | Docker, Railway, Vercel, CI/CD GitHub Actions, backups, Sentry |
| `aji-legal` | Compliance OAB, disclaimers obrigatórios, LGPD, termos de uso |
| `aji-product` | Backlog, priorização dos 60 dias, métricas, user stories |
| `aji-whatsapp` | Evolution API, onboarding WA, formatação (fase 2) |

---

## 12. Métricas de Sucesso

```
North Star:             Consultas jurídicas com satisfação ≥ 4/5
Conversão trial→pago:  meta 30%  (benchmark SaaS B2B: 15–25%)
Retenção 30 dias:       meta 70%
Retenção 90 dias:       meta 55%
Churn mensal:           meta < 5%
MRR mês 3:              meta R$ 10.000
Satisfação chat:        meta ≥ 4.2/5
% clientes via contador: meta 40%
Escalada p/ advogado:   meta < 15%  (muito alto = IA fraca; muito baixo = descartando casos sérios)
```

---

## 13. Identidade Visual

- **Paleta:** Azul naval `#070F1E` / `#132040` + Azul `#2563EB` + Dourado `#C8A96E` + Ciano `#38BDF8`
- **Fontes:** Bricolage Grotesque (display, bold) + Instrument Serif (italic, destaque) + Geist Mono (código/mono)
- **Logo:** Ícone de cérebro com circuitos + gradiente azul→dourado + letras "AJI" bold + tagline "Assistente Jurídico Inteligente"
- **Tom de voz:** Direto, claro, sem juridiquês — confiante mas acessível. Nunca pomposo.

---

## 14. Decisões Já Tomadas — Não Rediscutir

```
✅ Interface: chat livre + fluxos guiados (ambos)
✅ Canal MVP: somente web — WhatsApp é fase 2
✅ LLM: OpenAI (gpt-4o-mini default + gpt-4o para complexidade alta)
✅ Sem DeepSeek: LGPD incompatível, risco de reputação em produto jurídico
✅ Base jurídica: conteúdo já existe com o Julio — tarefa é estruturar para RAG
✅ Licença por CNPJ (não CPF) — contexto empresarial
✅ Comissão recorrente de 20% para contadores
✅ Modelo híbrido: IA + advogado humano para casos complexos
✅ Julio como responsável técnico jurídico formal (OAB)
✅ Trial 7 dias sem cartão de crédito
✅ Preços: R$ 197 / R$ 297 / R$ 397
✅ RAG com pgvector — tudo no PostgreSQL, sem Pinecone
✅ Evolution API no MVP (WhatsApp fase 2), Meta Business API em escala
✅ Deploy: Railway (backend) + Vercel (frontend) no MVP
```

---

## 15. Contexto para IA — System Prompt Base

```
Produto:    AJI — Assistente Jurídico Inteligente
Público:    Empresários PME brasileiros
Tom:        Claro, direto, sem juridiquês

Estrutura de toda resposta:
  1. Situação (o que está acontecendo juridicamente)
  2. Orientação (o que geralmente se faz / como funciona)
  3. Riscos (o que pode dar errado se agir incorretamente)
  4. Próximo passo (ação concreta + quando escalar ao advogado)

Regras obrigatórias:
  - Citar base legal quando relevante (ex: "art. 482 da CLT")
  - Disclaimer em toda resposta
  - Escalar ao advogado se: risco judicial, parecer formal, atuação processual
  - NUNCA garantir resultados
  - NUNCA chamar de "consultoria jurídica"
```

---

## 16. Regras de Segurança do Código (OBRIGATÓRIO)

### Multi-Tenancy — Regra Mais Crítica

**Toda query ao banco de dados DEVE incluir `tenant_id` como filtro.** Não existe exceção. Retornar dados cross-tenant é a vulnerabilidade mais grave possível neste sistema.

```python
# ❌ PROIBIDO — query sem tenant_id
result = await db.execute(select(Conversation).where(Conversation.id == conv_id))

# ✅ OBRIGATÓRIO — sempre filtrar por tenant
result = await db.execute(
    select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.tenant_id == current_tenant_id  # SEMPRE
    )
)
```

### Dados Sensíveis

Os seguintes dados NUNCA devem aparecer em logs, mensagens de erro ou respostas de API:

- CNPJ completo (mascarar: `XX.XXX.XXX/XXXX-XX` → `XX.***.***/**XX-XX`)
- Dados bancários do Partner (`bank_data`)
- `stripe_customer_id` e `stripe_subscription_id`
- Tokens JWT completos
- Conteúdo de conversas de outros tenants

### Disclaimer Jurídico Obrigatório

Toda resposta do AJI ao empresário DEVE incluir disclaimer. Sem exceção. Mesmo em respostas curtas, FAQ ou fluxos guiados. O agente `aji-legal` tem os templates oficiais.

### Validação de Input

Todo endpoint que recebe dados do usuário DEVE:
1. Validar com Pydantic schema (nunca confiar em input cru)
2. Sanitizar strings contra XSS
3. Verificar que o `tenant_id` do request corresponde ao token JWT
4. Rate limit por plano (Essencial=30/mês, Profissional=ilimitado)

---

## 17. Decisões Arquiteturais Compartilhadas

Consulte o arquivo `.claude/decisions.md` para ver todas as decisões técnicas já tomadas e seu status. Antes de propor uma decisão que já foi tomada, verifique esse arquivo.

---

*Última atualização: Março 2026 | Fase: Pré-MVP | Prazo: 60 dias*
*Atualizado com: Política anti-bajulação, regras de multi-tenancy, segurança de dados sensíveis*
