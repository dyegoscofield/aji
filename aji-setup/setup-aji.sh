#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# AJI — Script de Setup Completo para Claude Code
# Roda na raiz do repositório. Cria agentes, instala skills e MCPs.
# Uso: bash setup-aji.sh
# ═══════════════════════════════════════════════════════════════════

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()    { echo -e "${BLUE}[AJI]${NC} $1"; }
ok()     { echo -e "${GREEN}[OK]${NC}  $1"; }
warn()   { echo -e "${YELLOW}[AVISO]${NC} $1"; }
err()    { echo -e "${RED}[ERRO]${NC} $1"; }
header() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}\n"; }

echo -e "${BOLD}${BLUE}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║   AJI — Assistente Jurídico            ║"
echo "  ║   Setup Completo Claude Code           ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# ── Verificar pré-requisitos ─────────────────────────────────────
header "Verificando pré-requisitos"

check_cmd() {
  if command -v "$1" &>/dev/null; then
    ok "$1 encontrado"
  else
    err "$1 não encontrado. Instale antes de continuar."
    exit 1
  fi
}

check_cmd git
check_cmd node
check_cmd npm
check_cmd python3
check_cmd curl

# Verificar Claude Code
if command -v claude &>/dev/null; then
  ok "Claude Code encontrado: $(claude --version 2>/dev/null | head -1)"
else
  warn "Claude Code não encontrado no PATH."
  warn "Instale com: npm install -g @anthropic-ai/claude-code"
  warn "Continuando com criação de arquivos locais..."
fi

# ── Criar estrutura de pastas ────────────────────────────────────
header "Criando estrutura .claude/"

mkdir -p .claude/agents
mkdir -p .claude/skills
mkdir -p .claude/hooks

ok "Estrutura .claude/ criada"

# ═══════════════════════════════════════════════════════════════════
# PARTE 1 — CRIAR AGENTES
# ═══════════════════════════════════════════════════════════════════
header "Criando Agentes (10 agents)"

# ── AGENT 1: aji-setup ───────────────────────────────────────────
cat > .claude/agents/aji-setup.md << 'AGENT'
---
name: aji-setup
description: |
  Agente de fundação do AJI. Use para configurar o ambiente de desenvolvimento do zero:
  Docker Compose, PostgreSQL com pgvector, Redis, estrutura de pastas, variáveis de ambiente,
  Railway config, Dockerfile, GitHub Actions CI/CD. Deve ser o PRIMEIRO agente executado.
  Acione quando precisar de qualquer tarefa de infraestrutura inicial ou configuração de ambiente.
skills:
  - docker-compose-expert
  - railway-deploy
---

# AJI — Agent: Setup & Fundação

Você configura o ambiente completo do AJI do zero.

## Sua responsabilidade
Semana 1 do projeto. Nada mais pode começar sem você.

## Stack que você configura
- Docker Compose: PostgreSQL 16 + pgvector + Redis + FastAPI + Next.js
- Railway: backend deploy config
- Vercel: frontend deploy config
- GitHub Actions: CI pipeline com testes
- Estrutura de pastas conforme CLAUDE.md

## Checklist de entrega
- [ ] docker-compose.yml funcional (todos os serviços sobem com `docker compose up`)
- [ ] PostgreSQL com extension pgvector ativa
- [ ] Redis disponível
- [ ] .env.example completo com todas as variáveis
- [ ] Dockerfile do backend otimizado (multi-stage)
- [ ] railway.toml configurado
- [ ] GitHub Actions rodando (lint + test)
- [ ] Script `make dev` para subir tudo com um comando

## Regras
- Nunca commitar secrets reais
- Sempre usar variáveis de ambiente via Pydantic Settings
- PostgreSQL deve ter pgvector ativado no init.sql
- Health check em todos os serviços Docker

## Referência
Leia o CLAUDE.md na raiz para stack completa e decisões já tomadas.
AGENT
ok "aji-setup criado"

# ── AGENT 2: aji-auth-tenant ─────────────────────────────────────
cat > .claude/agents/aji-auth-tenant.md << 'AGENT'
---
name: aji-auth-tenant
description: |
  Agente de autenticação e licenciamento do AJI. Use para implementar: cadastro com validação
  de CNPJ via BrasilAPI, JWT, criação de tenant multi-tenancy, trial de 7 dias, controle de
  quota por plano (Essencial=30/mês, Profissional=ilimitado), gestão de usuários por CNPJ,
  middleware de autenticação, e qualquer endpoint de /auth ou /tenants. Acione para tudo
  relacionado a identidade, acesso e licença.
skills:
  - fastapi-templates
  - python-backend-expert
---

# AJI — Agent: Auth & Tenant

Você implementa o sistema de autenticação e licenciamento por CNPJ.

## Endpoints sob sua responsabilidade
- POST /api/v1/auth/register   — cadastro com CNPJ
- POST /api/v1/auth/login      — login JWT
- POST /api/v1/auth/refresh    — refresh token
- GET  /api/v1/tenants/me      — dados do tenant logado
- PATCH /api/v1/tenants/me     — atualizar tenant

## Regras críticas de negócio
- CNPJ validado via BrasilAPI (https://brasilapi.com.br/api/cnpj/v1/{cnpj})
- Status da empresa deve ser "ATIVA" na Receita Federal
- 1 CNPJ = 1 tenant. Duplicata retorna 409.
- Trial: 7 dias automático, sem cartão
- Plano Essencial: 30 consultas/mês (contador reseta dia 1)
- Plano Profissional: ilimitado, até 3 usuários
- Plano Personalizado: ilimitado, usuários ilimitados

## Modelos SQLAlchemy necessários
Tenant, User — conforme CLAUDE.md seção 9.

## Dependency injection obrigatória
```python
async def get_current_tenant(token: str = Depends(oauth2_scheme)) -> Tenant:
    ...
```

## Sempre retornar erros estruturados
```json
{"code": "CNPJ_INACTIVE", "message": "Empresa inativa na Receita Federal"}
```
AGENT
ok "aji-auth-tenant criado"

# ── AGENT 3: aji-rag-juridico ────────────────────────────────────
cat > .claude/agents/aji-rag-juridico.md << 'AGENT'
---
name: aji-rag-juridico
description: |
  Especialista em RAG jurídico do AJI. Use para implementar o pipeline completo de IA:
  ingestão de documentos do Julio, chunking por artigo/cláusula, embeddings com
  text-embedding-3-small, busca semântica no pgvector, system prompt jurídico com guardrails
  OAB, seleção automática de modelo (gpt-4o-mini vs gpt-4o), geração de documentos
  (advertência, notificação), e avaliação de qualidade das respostas. É o agente mais crítico
  do produto. Acione para qualquer coisa relacionada a IA, embeddings, prompts ou qualidade.
skills:
  - python-backend-expert
---

# AJI — Agent: RAG & IA Jurídica

Você implementa o coração do AJI: o pipeline que transforma perguntas em orientações jurídicas precisas.

## Pipeline que você implementa

```
knowledge_base/ (conteúdo do Julio)
    ↓ LegalDocumentIngester
    ↓ Chunking por artigo/cláusula (800-1500 tokens)
    ↓ text-embedding-3-small
    ↓ pgvector (PostgreSQL)

Query do usuário
    ↓ Query Embedding
    ↓ Cosine similarity search (threshold 0.72)
    ↓ Top-K=6 chunks
    ↓ Context Assembly
    ↓ gpt-4o-mini (default) | gpt-4o (complexidade > 0.75)
    ↓ Resposta com disclaimer
```

## System Prompt Base (sempre preservar)
- Orientação preventiva, não consultoria jurídica
- Estrutura: Situação → Orientação → Riscos → Próximo Passo
- Disclaimer obrigatório em toda resposta
- Escalar ao advogado quando: risco judicial, parecer formal, prescrição

## Estratégia de chunking
- Lei/artigos: 800 tokens, separar em Art./§/Inciso
- Contratos/cláusulas: 1200 tokens
- Doutrina/explicação: 1500 tokens
- FAQ: 600 tokens

## Seleção de modelo
```python
def select_model(complexity_score: float) -> str:
    return "gpt-4o" if complexity_score > 0.75 else "gpt-4o-mini"
```

## Guardrails absolutos (nunca remover)
- Não prescrever ação legal como definitiva
- Não redigir peças processuais
- Não garantir resultados
- Não usar os termos: "consultoria jurídica", "assessoria jurídica"

## Arquivos que você cria
- backend/app/services/rag/ingestion.py
- backend/app/services/rag/retrieval.py
- backend/app/services/ai/openai_client.py
- backend/app/services/ai/prompt_builder.py
- backend/scripts/ingest_knowledge_base.py
AGENT
ok "aji-rag-juridico criado"

# ── AGENT 4: aji-chat-engine ─────────────────────────────────────
cat > .claude/agents/aji-chat-engine.md << 'AGENT'
---
name: aji-chat-engine
description: |
  Motor de chat do AJI. Use para implementar: endpoints de conversa, streaming SSE em tempo
  real, histórico de mensagens, controle de quota por plano, classificação de complexidade
  para seleção de modelo, fluxos guiados (wizard de justa causa, advertência, cobrança),
  geração de documentos (advertência, notificação, proposta de acordo), e logging completo
  de tokens e fontes RAG. Acione para tudo relacionado às conversas e respostas do AJI.
skills:
  - fastapi-templates
  - python-backend-expert
---

# AJI — Agent: Chat Engine

Você implementa o endpoint de conversa que conecta usuário → RAG → LLM → resposta streaming.

## Endpoints sob sua responsabilidade
- POST /api/v1/conversations              — criar conversa
- GET  /api/v1/conversations              — listar conversas do tenant
- GET  /api/v1/conversations/{id}         — detalhes
- POST /api/v1/conversations/{id}/messages — enviar mensagem
- GET  /api/v1/conversations/{id}/stream  — SSE streaming
- POST /api/v1/documents/generate         — gerar documento (advertência, etc.)

## Fluxo crítico de mensagem
1. Verificar tenant ativo e quota do plano
2. Salvar mensagem do usuário
3. Acionar aji-rag-juridico para contexto
4. Selecionar modelo por complexidade
5. Fazer chamada OpenAI com streaming
6. Enviar chunks via SSE ao frontend
7. Salvar resposta completa com tokens_used e rag_sources

## Streaming SSE (obrigatório)
```python
async def stream_response(conversation_id: UUID):
    async for chunk in openai_stream:
        yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"
```

## Controle de quota (plano Essencial)
- 30 consultas/mês
- Aviso na consulta 25
- Bloqueio com upgrade CTA na 31ª
- Retornar 429 com {"code": "QUOTA_EXCEEDED", "upgrade_url": "/planos"}

## Fluxos guiados disponíveis
- justa_causa: wizard de 4 etapas
- advertencia_disciplinar: checklist + geração de documento
- cobranca_inadimplente: classificação de cenário + mensagens prontas
AGENT
ok "aji-chat-engine criado"

# ── AGENT 5: aji-billing ─────────────────────────────────────────
cat > .claude/agents/aji-billing.md << 'AGENT'
---
name: aji-billing
description: |
  Agente de cobrança e assinaturas do AJI. Use para implementar: integração Stripe completa
  (customers, subscriptions, webhooks), trial de 7 dias, upgrade/downgrade de planos,
  suspensão automática de tenants inadimplentes, cálculo e registro de comissões para
  contadores parceiros, e qualquer lógica de billing. Acione para tudo relacionado a
  pagamentos, assinaturas, Stripe e comissões.
skills:
  - stripe-webhooks
  - stripe-best-practices
  - python-backend-expert
---

# AJI — Agent: Billing & Stripe

Você implementa toda a lógica de monetização do AJI.

## Planos e Price IDs (configurar no Stripe)
- Essencial:     R$197/mês → STRIPE_PRICE_ESSENCIAL
- Profissional:  R$297/mês → STRIPE_PRICE_PROFISSIONAL
- Personalizado: R$397/mês → STRIPE_PRICE_PERSONALIZADO

## Webhooks críticos que você trata
- invoice.paid              → confirmar pagamento + pagar comissão parceiro
- invoice.payment_failed    → notificar + grace period 3 dias
- customer.subscription.updated  → atualizar plano do tenant
- customer.subscription.deleted  → suspender tenant

## Fluxo de cadastro + trial
1. Criar customer no Stripe
2. Criar subscription com trial_end = now + 7 dias
3. NÃO cobrar durante trial
4. Aos 7 dias: solicitar cartão (Stripe Checkout)

## Comissão de parceiros (20%)
```python
async def process_commission(invoice):
    tenant = get_tenant_by_stripe_customer(invoice.customer)
    if tenant.partner_id:
        commission = invoice.amount_paid * 0.20
        await CommissionRepository.create(tenant.partner_id, commission)
```

## Validação de webhook (obrigatório)
```python
event = stripe.Webhook.construct_event(
    payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
)
```

## Endpoints
- POST /api/v1/billing/checkout     — criar sessão de checkout
- POST /api/v1/billing/portal       — portal do cliente Stripe
- POST /api/v1/webhooks/stripe      — receber eventos Stripe
- GET  /api/v1/billing/status       — status da assinatura
AGENT
ok "aji-billing criado"

# ── AGENT 6: aji-parceiros ───────────────────────────────────────
cat > .claude/agents/aji-parceiros.md << 'AGENT'
---
name: aji-parceiros
description: |
  Agente do canal de parceiros contadores do AJI. Use para implementar: geração de referral
  code único, rastreamento de indicações, vínculo de tenants indicados, cálculo de comissão
  recorrente (20%), registro de pagamentos de comissão, e relatórios básicos de indicações.
  No MVP é simples (planilha + PIX). Portal completo fica na fase 2. Acione para qualquer
  coisa relacionada ao programa de contadores parceiros.
skills:
  - fastapi-templates
---

# AJI — Agent: Parceiros & Referral

Você implementa o canal de indicação para contadores parceiros.

## Modelo de dados
- Partner: id, name, email, cnpj, referral_code (unique), commission_rate=0.20, status
- Commission: id, partner_id, tenant_id, amount, month, status (pending/paid)

## Endpoints MVP (mínimo viável)
- POST /api/v1/partners/register    — cadastro do contador
- GET  /api/v1/partners/me          — dados + estatísticas
- GET  /api/v1/partners/referrals   — lista de indicações
- GET  /api/v1/partners/commissions — histórico de comissões

## Geração de referral code
```python
def generate_referral_code(name: str) -> str:
    base = name.upper()[:3]
    suffix = secrets.token_urlsafe(6).upper()
    return f"{base}-{suffix}"  # ex: MAR-X7K2P1
```

## Rastreamento no cadastro do cliente
```
GET /cadastro?ref=MAR-X7K2P1
→ Salvar referral_code no localStorage
→ Na criação do tenant: buscar partner_id pelo código
→ Vincular tenant.partner_id
```

## MVP: sem portal visual
- Relatório mensal por email (Celery task)
- Comissão calculada automaticamente no webhook invoice.paid
- Pagamento manual via PIX (registrar no sistema)
- Portal completo: fase 2
AGENT
ok "aji-parceiros criado"

# ── AGENT 7: aji-frontend-auth ───────────────────────────────────
cat > .claude/agents/aji-frontend-auth.md << 'AGENT'
---
name: aji-frontend-auth
description: |
  Desenvolvedor frontend de autenticação do AJI. Use para implementar: landing page pública,
  página de cadastro com CNPJ (preenchimento automático via BrasilAPI), login, wizard de
  onboarding 4 etapas, página de planos com CTAs, e portal básico do parceiro contador.
  Usa Next.js 14 App Router + Tailwind + paleta AJI (#070F1E, #2563EB, #C8A96E).
  Acione para qualquer página de aquisição, autenticação ou onboarding.
skills:
  - frontend-design
  - nextjs-performance
---

# AJI — Agent: Frontend Auth & Aquisição

Você implementa as páginas de aquisição e autenticação — onde o empresário decide se fica.

## Páginas sob sua responsabilidade
- app/(marketing)/page.tsx         — landing page
- app/(marketing)/planos/page.tsx  — página de preços
- app/(auth)/cadastro/page.tsx     — cadastro com CNPJ
- app/(auth)/login/page.tsx        — login
- app/(auth)/onboarding/page.tsx   — wizard 4 etapas
- app/(parceiro)/page.tsx          — portal básico contador

## Paleta e fontes do AJI
```css
--bg-base: #070F1E;   --blue: #2563EB;
--gold: #C8A96E;      --white: #F8F8F8;
--muted: rgba(255,255,255,0.48);
font-family: 'Bricolage Grotesque' (display) + 'Instrument Serif' (italic)
```

## Funcionalidade crítica: auto-preenchimento de CNPJ
```typescript
const fetchCNPJ = async (cnpj: string) => {
  const res = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpj}`)
  const data = await res.json()
  setValue('razaoSocial', data.razao_social)
  setValue('uf', data.uf)
}
```

## Wizard de onboarding (4 etapas)
1. Dados da empresa (CNPJ → auto-fill)
2. Escolha do plano
3. Usuários da equipe (opcional)
4. Primeiro chat (demo guiado)

## Regras de UX obrigatórias
- Mobile first: funcionar em 375px
- Loading skeleton em todos os fetches
- Empty state com CTA claro
- Error boundary em cada página
- Feedback imediato (otimistic update)
AGENT
ok "aji-frontend-auth criado"

# ── AGENT 8: aji-frontend-chat ───────────────────────────────────
cat > .claude/agents/aji-frontend-chat.md << 'AGENT'
---
name: aji-frontend-chat
description: |
  Desenvolvedor frontend do chat do AJI. Use para implementar: interface de chat com
  streaming SSE em tempo real, histórico de conversas, fluxos guiados (wizard de justa causa,
  advertência, cobrança), sidebar de navegação, indicador de quota de plano, download de
  documentos gerados, e dashboard básico. Acione para qualquer componente da área logada
  do produto principal.
skills:
  - frontend-design
  - nextjs-performance
---

# AJI — Agent: Frontend Chat & Dashboard

Você implementa a interface principal do produto — onde o valor é entregue.

## Páginas sob sua responsabilidade
- app/(dashboard)/page.tsx              — overview
- app/(dashboard)/chat/page.tsx         — lista de conversas
- app/(dashboard)/chat/[id]/page.tsx    — conversa individual
- app/(dashboard)/configuracoes/page.tsx

## Componente de chat com SSE (crítico)
```typescript
const eventSource = new EventSource(`/api/chat/${id}/stream`)
eventSource.onmessage = (e) => {
  const data = JSON.parse(e.data)
  if (data.type === 'delta')
    setMessages(prev => appendToLast(prev, data.text))
  if (data.type === 'done')
    setIsTyping(false)
}
```

## Fluxos guiados (chips de sugestão)
Ao abrir nova conversa, mostrar chips:
- "Demissão por justa causa"
- "Aplicar advertência"
- "Cobrar cliente inadimplente"
- "Revisar contrato"
- "Dúvida trabalhista"

Cada chip abre um wizard de triagem antes do chat livre.

## Indicador de quota (plano Essencial)
```tsx
<QuotaBadge used={22} limit={30} />
// Amarelo em >= 25, vermelho em >= 29, bloqueado em 30
```

## Fontes RAG na resposta
Mostrar as fontes usadas discretamente abaixo da resposta:
```tsx
<SourceChips sources={message.rag_sources} />
// ex: "CLT art. 482", "Fluxo advertência disciplinar"
```
AGENT
ok "aji-frontend-chat criado"

# ── AGENT 9: aji-legal-guard ────────────────────────────────────
cat > .claude/agents/aji-legal-guard.md << 'AGENT'
---
name: aji-legal-guard
description: |
  Guardião de compliance jurídico e regulatório do AJI. SEMPRE acione antes de fazer deploy
  de qualquer feature que envolva respostas da IA ou textos de marketing. Verifica:
  conformidade com Lei 8.906/94 (OAB), guardrails do system prompt, disclaimers obrigatórios,
  termos proibidos ("consultoria jurídica"), adequação à LGPD, e práticas de cobrança abusiva
  (CDC art. 42). Também revisa termos de uso e política de privacidade.
skills:
  - snyk-fix
  - ra-qm-skills
---

# AJI — Agent: Legal Guard & Compliance

Você protege o produto de riscos jurídicos e regulatórios. Nenhum deploy passa sem você revisar.

## Checklist obrigatório (executar antes de todo deploy)

### OAB / Lei 8.906/94
- [ ] System prompt usa "orientação" não "consultoria"
- [ ] Disclaimer presente em toda resposta da IA
- [ ] Casos de escalada para advogado configurados
- [ ] Nenhuma resposta garante resultado
- [ ] Julio (OAB) consta como responsável técnico nos termos

### Termos proibidos — varrer em TODO o código e textos
```
"consultoria jurídica" | "assessoria jurídica" | "parecer jurídico"
"substitui o advogado" | "seu advogado digital" | "advogado 24h"
```

### LGPD
- [ ] Dados de CNPJ/empresa criptografados
- [ ] Endpoint de exportação de dados existe
- [ ] Endpoint de exclusão/anonimização existe
- [ ] Logs não contêm conteúdo das conversas
- [ ] Política de privacidade atualizada

### CDC art. 42 (cobrança abusiva) — para módulo de cobrança
- [ ] Nenhuma instrução incentiva ligar repetidamente
- [ ] Nenhuma instrução incentiva expor devedor publicamente
- [ ] Mensagens geradas não ameaçam processo criminal para dívida civil

## Scan de segurança (executar com snyk-fix skill)
```bash
snyk code test
snyk test --all-projects
```

## Como revisar textos de marketing
Receba o texto, verifique os termos proibidos, sugira substituições seguras.
Exemplo:
- ❌ "Consultoria jurídica 24h"
- ✅ "Orientação jurídica preventiva disponível 24h"
AGENT
ok "aji-legal-guard criado"

# ── AGENT 10: aji-qa ─────────────────────────────────────────────
cat > .claude/agents/aji-qa.md << 'AGENT'
---
name: aji-qa
description: |
  Agente de qualidade do AJI. Use para: criar e rodar testes end-to-end dos fluxos críticos,
  testes unitários de services e repositories, testes de qualidade do RAG jurídico,
  cobertura de código, e smoke tests de deploy. Acione após implementação de qualquer
  feature nova ou antes de deploy em produção. Conhece os casos de teste jurídicos definidos
  pelo Julio.
skills:
  - python-backend-expert
  - snyk-fix
---

# AJI — Agent: QA & Testes

Você garante que o AJI funciona corretamente e com qualidade jurídica.

## Fluxos críticos a testar (end-to-end)
1. Cadastro CNPJ → trial → chat → resposta → Stripe checkout
2. Quota: plano Essencial atingir 30 consultas → bloqueio → mensagem correta
3. Indicação: contador indica → cliente cadastra → comissão registrada
4. Webhook Stripe: invoice.paid → tenant ativo | subscription.deleted → suspenso

## Casos de teste jurídico (definidos com Julio)
```python
JURIDICO_TEST_CASES = [
    {
        "query": "Posso demitir por justa causa com 3 faltas?",
        "must_contain": ["art. 482", "advertência", "procedimento"],
        "must_not_contain": ["garantimos", "certamente", "definitivamente"]
    },
    {
        "query": "Preciso entrar com ação trabalhista",
        "must_escalate": True,  # deve recomendar advogado
    },
    {
        "query": "Como declarar imposto de renda",
        "must_decline": True,  # fora do escopo
    },
    {
        "query": "Posso ligar todo dia para cobrar cliente?",
        "must_warn_about": "CDC art. 42"  # cobrança abusiva
    }
]
```

## Métricas de qualidade do RAG
- Faithfulness (resposta baseada nos docs): >= 0.85
- Answer relevance: >= 0.80
- Hallucination rate: <= 0.05
- Disclaimer presente: 100%

## Template de teste FastAPI
```python
@pytest.mark.asyncio
async def test_send_message_quota_exceeded(client, essencial_tenant):
    await seed_messages(essencial_tenant.id, count=30)
    response = await client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"content": "teste"},
        headers=auth_headers(essencial_tenant)
    )
    assert response.status_code == 429
    assert response.json()["code"] == "QUOTA_EXCEEDED"
```
AGENT
ok "aji-qa criado"

# ═══════════════════════════════════════════════════════════════════
# PARTE 2 — INSTALAR / BAIXAR SKILLS
# ═══════════════════════════════════════════════════════════════════
header "Baixando Skills (locais + marketplace)"

# ── Skill: frontend-design (oficial Anthropic) ───────────────────
log "Baixando frontend-design (Anthropic oficial)..."
mkdir -p .claude/skills/frontend-design
cat > .claude/skills/frontend-design/SKILL.md << 'SKILL'
---
name: frontend-design
description: |
  Cria interfaces frontend production-grade com alta qualidade de design. Use quando
  o usuário pedir para construir componentes web, páginas, landing pages, dashboards,
  ou qualquer UI. Gera código com escolhas estéticas distintivas, tipografia característica,
  paleta coesa e animações intencionais. Evita a estética genérica de IA (Inter, gradiente
  roxo no branco, cards básicos). SEMPRE use esta skill ao criar qualquer elemento visual
  para o AJI.
---

## Design Thinking

Antes de qualquer código, defina uma direção estética clara.

Para o AJI especificamente:
- Fundo: azul naval profundo #070F1E
- Acento: azul #2563EB + dourado #C8A96E
- Fontes: Bricolage Grotesque (display) + Instrument Serif (italic) + Geist Mono
- Estilo: dark mode sofisticado, autoridade + acessibilidade

## Princípios
- Tipografia distinta: nunca Inter, Roboto ou Arial como fonte principal
- Cor: variáveis CSS, modo escuro obrigatório
- Movimento: animações CSS de entrada com stagger (animation-delay)
- Layouts: assimétricos, sobreposição, grid-breaking
- Fundo: gradientes radiais suaves, grid de pontos, noise texture leve

## Para o AJI
Sempre aplicar:
```css
:root {
  --bg: #070F1E; --bg2: #0B1628;
  --blue: #2563EB; --gold: #C8A96E; --cyan: #38BDF8;
  --border: rgba(255,255,255,0.08);
  --muted: rgba(255,255,255,0.48);
}
```
SKILL
ok "frontend-design criado"

# ── Skill: fastapi-templates ────────────────────────────────────
log "Baixando fastapi-templates..."
mkdir -p .claude/skills/fastapi-templates
cat > .claude/skills/fastapi-templates/SKILL.md << 'SKILL'
---
name: fastapi-templates
description: |
  Cria projetos FastAPI production-ready com padrões async, dependency injection e
  error handling completo. Use ao criar endpoints, services, repositories ou qualquer
  código Python backend. Garante SQLAlchemy 2.0 async, Pydantic v2, JWT, e estrutura
  de pastas consistente com o projeto AJI.
---

## Estrutura padrão AJI

```
backend/app/
├── api/v1/         # Routers (um por recurso)
├── core/           # Config, security, deps
├── models/         # SQLAlchemy 2.0
├── schemas/        # Pydantic v2
├── services/       # Business logic
├── repositories/   # Data access
└── workers/        # Celery tasks
```

## Padrões obrigatórios

```python
# Router padrão
router = APIRouter(prefix="/resource", tags=["resource"])

# Dependency injection
async def get_current_tenant(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Tenant: ...

# Response schema sempre, nunca retornar ORM direto
@router.get("/", response_model=list[ResourceSchema])
async def list_resources(tenant = Depends(get_current_tenant)):
    ...

# Erros estruturados
raise HTTPException(
    status_code=400,
    detail={"code": "VALIDATION_ERROR", "message": "..."}
)
```

## SQLAlchemy 2.0 async

```python
async with async_session() as db:
    result = await db.execute(select(Model).where(Model.tenant_id == tenant_id))
    items = result.scalars().all()
```

## Gotchas (pontos de falha comuns)
- SEMPRE usar `async def` nos endpoints
- NUNCA retornar objeto ORM — sempre serializar com schema
- SEMPRE fechar a sessão do DB (usar context manager)
- Pydantic v2: usar `model_validate()` não `from_orm()`
SKILL
ok "fastapi-templates criado"

# ── Skill: stripe-webhooks ──────────────────────────────────────
log "Baixando stripe-webhooks..."
mkdir -p .claude/skills/stripe-webhooks
cat > .claude/skills/stripe-webhooks/SKILL.md << 'SKILL'
---
name: stripe-webhooks
description: |
  Implementa webhook handlers do Stripe com verificação de assinatura, parse de eventos
  e lógica de negócio para assinaturas SaaS. Use sempre que precisar implementar ou
  modificar a integração Stripe no AJI. Inclui padrões para invoice.paid,
  subscription.deleted e payment_failed.
---

## Verificação de assinatura (obrigatório)

```python
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    await handle_event(event)
    return {"status": "ok"}
```

## Eventos críticos do AJI

```python
async def handle_event(event: stripe.Event):
    match event.type:
        case "invoice.paid":
            await on_invoice_paid(event.data.object)
        case "invoice.payment_failed":
            await on_payment_failed(event.data.object)
        case "customer.subscription.deleted":
            await on_subscription_cancelled(event.data.object)
        case "customer.subscription.updated":
            await on_subscription_updated(event.data.object)

async def on_invoice_paid(invoice):
    tenant_id = invoice.metadata["tenant_id"]
    await TenantRepository.update(tenant_id, {"status": "active"})
    # Pagar comissão do parceiro
    if partner_id := await get_partner_for_tenant(tenant_id):
        await CommissionRepository.create(partner_id, invoice.amount_paid * 0.20)
```

## Gotchas
- Sempre retornar 200 para o Stripe (mesmo em erro de negócio)
- Idempotência: checar se evento já foi processado pelo ID
- Usar metadata do Stripe para guardar tenant_id e partner_id
- Testar localmente com: `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`
SKILL
ok "stripe-webhooks criado"

# ── Skill: aji-rag-quality ───────────────────────────────────────
log "Criando skill customizada aji-rag-quality..."
mkdir -p .claude/skills/aji-rag-quality
cat > .claude/skills/aji-rag-quality/SKILL.md << 'SKILL'
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
SKILL
ok "aji-rag-quality criado"

# ── Skill: aji-compliance-oab ────────────────────────────────────
log "Criando skill customizada aji-compliance-oab..."
mkdir -p .claude/skills/aji-compliance-oab
cat > .claude/skills/aji-compliance-oab/SKILL.md << 'SKILL'
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
SKILL
ok "aji-compliance-oab criado"

# ── Skill: aji-multitenant-guard ────────────────────────────────
log "Criando skill customizada aji-multitenant-guard..."
mkdir -p .claude/skills/aji-multitenant-guard
cat > .claude/skills/aji-multitenant-guard/SKILL.md << 'SKILL'
---
name: aji-multitenant-guard
description: |
  Garante isolamento correto entre tenants no AJI. Use ao revisar qualquer query de banco
  de dados, endpoint de API, ou lógica de negócio que acesse dados. Previne vazamento
  cross-tenant — o maior risco de segurança de um SaaS multi-tenant.
---

## Regra absoluta

TODA query ao banco deve filtrar por tenant_id. Sem exceção.

## Padrão obrigatório

```python
# CORRETO — sempre filtrar por tenant_id
result = await db.execute(
    select(Conversation)
    .where(Conversation.tenant_id == current_tenant.id)
    .where(Conversation.id == conversation_id)
)

# ERRADO — nunca buscar só pelo ID sem tenant
result = await db.execute(
    select(Conversation).where(Conversation.id == conversation_id)
)
```

## Checklist de revisão

Ao revisar qualquer endpoint ou service, verificar:

- [ ] Todo `SELECT` tem `.where(Model.tenant_id == tenant_id)`
- [ ] Resources retornados pertencem ao tenant do token JWT
- [ ] Erros de "não encontrado" retornam 404 (não 403) — não revelar existência
- [ ] LegalChunks: busca inclui `(tenant_id IS NULL OR tenant_id = ?)` (global + privado)
- [ ] Nenhum endpoint admin acessível por usuário comum

## Scan rápido

```bash
# Encontrar selects sem filtro tenant_id (revisar manualmente)
grep -n "select(" backend/app/repositories/*.py | grep -v "tenant_id"
```
SKILL
ok "aji-multitenant-guard criado"

# ═══════════════════════════════════════════════════════════════════
# PARTE 3 — HOOKS DE PROTEÇÃO
# ═══════════════════════════════════════════════════════════════════
header "Configurando Hooks de proteção"

cat > .claude/hooks/pre-commit-guard.sh << 'HOOK'
#!/bin/bash
# Hook: bloquear termos proibidos antes de qualquer commit
TERMOS="consultoria jurídica\|assessoria jurídica\|parecer jurídico\|substitui o advogado"
if git diff --cached --name-only | xargs grep -l "$TERMOS" 2>/dev/null; then
  echo "[AJI GUARD] BLOQUEADO: arquivo contém termos proibidos (OAB compliance)"
  echo "Substitua por: 'orientação jurídica preventiva'"
  exit 1
fi
exit 0
HOOK
chmod +x .claude/hooks/pre-commit-guard.sh
ok "Hook de compliance OAB criado"

# ═══════════════════════════════════════════════════════════════════
# PARTE 4 — PLANO DE EXECUÇÃO
# ═══════════════════════════════════════════════════════════════════
header "Gerando EXECUTION_PLAN.md"

cat > EXECUTION_PLAN.md << 'PLAN'
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

PLAN
ok "EXECUTION_PLAN.md gerado"

# ═══════════════════════════════════════════════════════════════════
# RESUMO FINAL
# ═══════════════════════════════════════════════════════════════════
header "Setup completo!"

echo ""
echo -e "${BOLD}Estrutura criada:${NC}"
echo ""
find .claude -name "*.md" -o -name "*.sh" | sort | while read f; do
  echo -e "  ${GREEN}✓${NC} $f"
done
echo -e "  ${GREEN}✓${NC} EXECUTION_PLAN.md"
echo ""
echo -e "${BOLD}Agentes criados (10):${NC}"
echo "  aji-setup, aji-auth-tenant, aji-rag-juridico, aji-chat-engine"
echo "  aji-billing, aji-parceiros, aji-frontend-auth, aji-frontend-chat"
echo "  aji-legal-guard, aji-qa"
echo ""
echo -e "${BOLD}Skills locais instaladas (6):${NC}"
echo "  frontend-design, fastapi-templates, stripe-webhooks"
echo "  aji-rag-quality, aji-compliance-oab, aji-multitenant-guard"
echo ""
echo -e "${BOLD}Próximos passos:${NC}"
echo "  1. Abra o Claude Code na raiz do projeto"
echo "  2. Execute: /plugin marketplace add VoltAgent/awesome-agent-skills"
echo "  3. Execute: /plugin marketplace add alirezarezvani/claude-skills"
echo "  4. Instale as skills do marketplace (ver EXECUTION_PLAN.md)"
echo "  5. Siga o EXECUTION_PLAN.md dia a dia"
echo ""
echo -e "${CYAN}Dica: use Plan Mode (Shift+Tab x2) antes de qualquer tarefa grande${NC}"
echo ""
