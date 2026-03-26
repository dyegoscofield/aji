# AJI — Custom Agents para Claude Code

Este diretório contém os Sub-Agents especializados para o desenvolvimento do **AJI (Assistente Jurídico Inteligente)**.

## Agents Disponíveis

| Agent | Responsabilidade | Skills de Apoio | Quando acionar |
|-------|-----------------|-----------------|----------------|
| `aji-architect` | Arquitetura, decisões técnicas, stack, modelos de dados | — | Decisões de design, integração entre módulos |
| `aji-backend` | FastAPI, SQLAlchemy, Stripe, CNPJ, autenticação | `aji-backend/` (4 skills) | Endpoints, serviços, migrations, testes |
| `aji-rag` | Pipeline de IA, embeddings, prompts, qualidade | `aji-rag/` (4 skills) | Respostas da IA, base de conhecimento, RAG |
| `aji-frontend` | Next.js, Tailwind, chat UI, dashboard, portal parceiro | `ui-ux-pro-max/` | Componentes, páginas, UX, animações |
| `aji-devops` | Docker, Railway, Vercel, CI/CD, monitoramento | — | Deploy, infra, variáveis de ambiente |
| `aji-legal` | Compliance OAB, LGPD, disclaimers, termos de uso | `aji-legal/` (4 skills) | Antes de lançar features jurídicas |
| `aji-product` | Backlog, roadmap, métricas, decisões de produto | — | Priorização, user stories, estratégia |
| `aji-whatsapp` | Integração WhatsApp, Evolution API, onboarding WA | — | Canal WhatsApp, webhooks, formatação |

## Estrutura de Skills (Carregamento Sob Demanda)

```
.claude/skills/
├── aji-backend/        → auth-cnpj, stripe-billing, celery-workers, api-patterns
├── aji-rag/            → system-prompt, ingestion-pipeline, retrieval-search, quality-guardrails
├── aji-legal/          → oab-compliance, disclaimers-compliance, lgpd-requirements, feature-checklist
└── ui-ux-pro-max/      → estilos, paletas, componentes (skill de mercado)
```

Cada skill tem um `SKILL.md` com índice dos recursos. O agente carrega apenas o recurso necessário para a tarefa atual, economizando ~40% de contexto.

## Prompt Files (Atalhos Rápidos)

```
.claude/prompts/
├── quick-compliance-check.md    → Verificação rápida de compliance OAB
├── quick-bug-diagnosis.md       → Diagnóstico rápido de bug
├── quick-prompt-review.md       → Revisão rápida de system prompt
└── quick-architecture-diagram.md → Diagrama Mermaid rápido
```

## Arquivos Globais

| Arquivo | Função |
|---------|--------|
| `CLAUDE.md` | Regras globais (anti-bajulação, multi-tenancy, dados sensíveis) |
| `.claude/decisions.md` | Decisões arquiteturais (ADRs) — consultar antes de propor mudanças |
| `.claude/settings.json` | Hooks de proteção (guard destrutivo, quality gate, transparência) |
| `.claude/base conhecimento/` | PDFs de legislação e jurisprudência para o RAG |

## Como Usar no Claude Code

No Claude Code, os agents são acionados automaticamente quando você descreve uma tarefa relacionada ao escopo deles. Você também pode acioná-los explicitamente:

```
@aji-backend criar endpoint de cadastro com validação de CNPJ
@aji-rag revisar o system prompt para casos de justa causa
@aji-legal verificar compliance da nova feature de chat
```

## Fluxo de Trabalho Recomendado

```
Nova feature
     ↓
aji-product (definir escopo e critérios)
     ↓
aji-legal (verificar compliance OAB se aplicável)
     ↓
aji-architect (decisão técnica — consultar decisions.md)
     ↓
aji-backend + aji-frontend (implementação — carregar skills relevantes)
     ↓
aji-rag (se envolver respostas da IA — consultar base conhecimento)
     ↓
aji-devops (deploy)
```

## Regras Universais (CLAUDE.md)

1. **Anti-bajulação:** Embasamento técnico/teórico sempre. Discordar quando necessário.
2. **Multi-tenancy:** Toda query DEVE incluir `tenant_id`.
3. **Dados sensíveis:** NUNCA expor CNPJ completo, bank_data, stripe IDs em logs.
4. **Decisões:** Consultar `.claude/decisions.md` antes de propor qualquer decisão arquitetural.
5. **Não-ação:** Não fazer nada que o usuário não pediu explicitamente.
