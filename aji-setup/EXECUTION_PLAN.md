# AJI — Plano de Execução para Claude Code
**Prazo:** 40 dias com agents paralelos | **Time:** Dyego + Dev2 + Julio

---

## Como usar os agents

No Claude Code, inicie cada sessão indicando o agent:
```
Use the aji-setup agent to configure Docker Compose for the project
Use the aji-rag-juridico agent to implement the document ingestion pipeline
```

Ou na conversa:
```
@aji-billing implement the Stripe subscription flow
@aji-legal-guard review this PR before deploy
```

---

## FASE 1 — Fundação (Dias 1–7)

### Dia 1–3: Setup (Dyego sozinho)
**Agent:** `aji-setup`
**Skills:** docker-compose-expert, railway-deploy

```
Tarefa para Claude Code:
"Use aji-setup agent. Create the complete development environment:
Docker Compose with PostgreSQL 16 + pgvector + Redis + FastAPI skeleton.
Include health checks, .env.example, Makefile with `make dev` command,
and GitHub Actions CI pipeline. Reference CLAUDE.md for the stack."
```

Critério de conclusão: `make dev` sobe todos os serviços sem erro.

### Dia 4–7: Auth + RAG em paralelo
**Dyego** → `aji-auth-tenant` | **Dev2** → `aji-rag-juridico`

```
Dyego → Claude Code:
"Use aji-auth-tenant agent. Implement the complete auth system:
CNPJ registration with BrasilAPI validation, JWT, tenant creation,
7-day trial, quota control by plan. Follow CLAUDE.md data models."

Dev2 → Claude Code:
"Use aji-rag-juridico agent. Implement the RAG pipeline:
Document ingestion from knowledge_base/, chunking by article/clause,
embeddings with text-embedding-3-small, pgvector storage,
semantic search with cosine similarity, and the base system prompt."
```

---

## FASE 2 — Core do Produto (Dias 8–21)

### Dia 8–14
**Dyego** → `aji-chat-engine` | **Dev2** → `aji-billing`

```
Dyego:
"Use aji-chat-engine agent. Implement conversation endpoints with
SSE streaming, quota control, complexity scoring for model selection,
and the 3 guided flows: justa_causa, advertencia, cobranca."

Dev2:
"Use aji-billing agent + stripe-webhooks skill. Implement complete
Stripe integration: customer creation, subscriptions with 7-day trial,
webhooks for invoice.paid and subscription.deleted, and partner
commission calculation (20%)."
```

### Dia 15–21: Frontend Auth
**Dev2** → `aji-frontend-auth`

```
Dev2:
"Use aji-frontend-auth agent + frontend-design skill.
Build the public landing page and auth pages: CNPJ registration
with BrasilAPI auto-fill, 4-step onboarding wizard, and plans page.
Use AJI design system: #070F1E background, #2563EB blue, #C8A96E gold,
Bricolage Grotesque font."
```

---

## FASE 3 — Interface e Parceiros (Dias 22–32)

### Dia 22–28
**Dyego** → `aji-frontend-chat` | **Dev2** → `aji-parceiros`

```
Dyego:
"Use aji-frontend-chat agent + frontend-design skill.
Build the chat interface with SSE streaming display, message bubbles,
typing indicator, RAG source chips, quota badge, and suggested topic
chips for new conversations."

Dev2:
"Use aji-parceiros agent. Implement the partner referral system:
unique code generation, referral tracking on tenant registration,
commission recording, and basic partner stats endpoint."
```

---

## FASE 4 — Qualidade e Deploy (Dias 33–40)

### Dia 33–37: QA completo
**Ambos** → `aji-qa` + `aji-legal-guard`

```
"Use aji-qa agent. Run the complete test suite:
1. End-to-end flow: CNPJ signup → trial → chat → Stripe checkout
2. Quota enforcement: Essencial plan at 30 messages
3. RAG quality: run all juridico test cases defined in the agent
4. Partner referral: code → signup → commission recorded

Then use aji-legal-guard agent + aji-compliance-oab skill to:
1. Scan all files for prohibited terms
2. Verify disclaimers in all AI responses
3. Check LGPD compliance endpoints
4. Run snyk security scan"
```

### Dia 38–40: Deploy e smoke tests
**Dyego** → `aji-setup` (deploy mode)

```
"Use aji-setup agent. Deploy to production:
1. Push backend to Railway (main branch)
2. Push frontend to Vercel
3. Run smoke tests: health check, test chat, test Stripe webhook
4. Verify CNPJ validation is working
5. Send test referral link and confirm tracking"
```

---

## Referência de Skills por Agent

| Agent | Skills instaladas |
|-------|------------------|
| aji-setup | docker-compose (marketplace) |
| aji-auth-tenant | fastapi-templates ✅ + python-backend-expert (marketplace) |
| aji-rag-juridico | python-backend-expert (marketplace) + aji-rag-quality ✅ |
| aji-chat-engine | fastapi-templates ✅ + python-backend-expert (marketplace) |
| aji-billing | stripe-webhooks ✅ + stripe-best-practices (marketplace) |
| aji-parceiros | fastapi-templates ✅ |
| aji-frontend-auth | frontend-design ✅ + nextjs-performance (marketplace) |
| aji-frontend-chat | frontend-design ✅ + nextjs-performance (marketplace) |
| aji-legal-guard | aji-compliance-oab ✅ + snyk-fix (marketplace) |
| aji-qa | python-backend-expert (marketplace) + aji-rag-quality ✅ |

✅ = já instalada localmente em .claude/skills/
(marketplace) = instalar pelo Claude Code /plugin

---

## Skills do Marketplace para instalar (executar no Claude Code)

```bash
# Adicionar marketplaces
/plugin marketplace add VoltAgent/awesome-agent-skills
/plugin marketplace add alirezarezvani/claude-skills

# Instalar skills
/plugin install stripe/stripe-best-practices@awesome-agent-skills
/plugin install nextjs-performance@awesome-agent-skills
/plugin install engineering-advanced-skills@claude-code-skills
/plugin install ra-qm-skills@claude-code-skills
```

Para python-backend-expert e snyk-fix: instalar manualmente via:
- python-backend-expert: https://mcpmarket.com/tools/skills/python-backend-expert
- snyk-fix: https://github.com/snyk/studio-recipes

---

## Regras do dia a dia

1. **Sempre abrir Plan Mode** (`Shift+Tab` duas vezes) antes de tarefas que tocam 3+ arquivos
2. **aji-legal-guard primeiro** em qualquer PR com IA ou marketing
3. **aji-qa depois** de qualquer feature nova
4. **Nunca pular** o critério de conclusão de cada fase
5. **CLAUDE.md é a lei** — conflito entre agent e CLAUDE.md: CLAUDE.md ganha

