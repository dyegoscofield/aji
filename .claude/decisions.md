# Decisões Arquiteturais — AJI

> Este arquivo é a fonte única de verdade para decisões técnicas do projeto. Todos os agentes devem consultar este arquivo antes de propor decisões. Se uma decisão já foi tomada, não rediscutir — apenas referenciar.

---

## Decisões Tomadas (Não Rediscutir)

### ADR-001: LLM — OpenAI com dois modelos
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** gpt-4o-mini (90% das consultas) + gpt-4o (10%, alta complexidade)
- **Motivo:** Melhor custo-benefício para RAG jurídico. DeepSeek descartado por LGPD. Claude descartado por custo em escala.
- **Agente responsável:** aji-architect

### ADR-002: Embedding — text-embedding-3-small
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** OpenAI text-embedding-3-small (1536 dimensões)
- **Motivo:** Custo baixo, qualidade suficiente para base jurídica estruturada, compatível com pgvector
- **Agente responsável:** aji-rag

### ADR-003: Chunking — Diferenciado por tipo de documento
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** Legislação=800 tokens, Contratos=1200 tokens, Doutrina/Fluxos=1500 tokens
- **Motivo:** Legislação tem artigos curtos e independentes. Contratos e fluxos precisam de mais contexto para manter coerência.
- **Agente responsável:** aji-rag

### ADR-004: Banco de dados — PostgreSQL + pgvector
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** Tudo no PostgreSQL (relacional + vetorial). Sem Pinecone ou banco vetorial separado.
- **Motivo:** Simplifica operação, reduz custos, pgvector é suficiente para o volume do MVP (<100k chunks)
- **Agente responsável:** aji-architect

### ADR-005: Deploy MVP — Railway + Vercel
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** Railway (backend FastAPI + PostgreSQL + Redis) + Vercel (frontend Next.js)
- **Motivo:** Setup rápido, custo previsível, migração para AWS ECS planejada para escala
- **Agente responsável:** aji-devops

### ADR-006: Auth — JWT + CNPJ via BrasilAPI
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** JWT para sessão, validação de CNPJ via BrasilAPI (gratuita), licença por CNPJ
- **Motivo:** CNPJ como identificador primário do tenant, BrasilAPI sem custo, JWT stateless para escala
- **Agente responsável:** aji-backend

### ADR-007: Pagamentos — Stripe
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** Stripe para assinaturas recorrentes, trial 7 dias sem cartão
- **Motivo:** Padrão de mercado SaaS, webhooks confiáveis, suporte a BRL
- **Agente responsável:** aji-backend

### ADR-008: Canal MVP — Somente Web
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** MVP apenas web. WhatsApp é fase 2 (Evolution API → Meta Business API)
- **Motivo:** Reduz escopo do MVP, evita complexidade de compliance WhatsApp Business
- **Agente responsável:** aji-product

### ADR-009: Interface — Chat livre + Fluxos guiados
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** Ambos. Chat como interface principal, fluxos para situações de alto risco
- **Motivo:** Chat é diferencial de UX, fluxos garantem qualidade jurídica em casos críticos
- **Agente responsável:** aji-product

### ADR-010: Responsável Técnico — Julio (OAB)
- **Status:** Aprovada
- **Data:** Março 2026
- **Decisão:** Julio como responsável técnico jurídico formal. Nome e OAB nos termos de uso.
- **Motivo:** Requisito regulatório (Lei 8.906/94). Sem advogado inscrito = exercício ilegal.
- **Agente responsável:** aji-legal

---

## Decisões Pendentes

### ADR-011: Estratégia de histórico de conversa
- **Status:** Pendente
- **Opções:** (a) Últimas N mensagens, (b) Resumo automático, (c) Sliding window com resumo
- **Contexto:** Afeta custo de tokens e qualidade das respostas em conversas longas
- **Agente responsável:** aji-rag
- **Prazo:** Semana 3-4

### ADR-012: Estratégia de escalada para advogado
- **Status:** Pendente
- **Opções:** (a) Threshold de confiança da IA, (b) Palavras-chave de risco, (c) Classificador dedicado
- **Contexto:** Meta é <15% de escalada. Muito alto = IA fraca, muito baixo = risco jurídico
- **Agente responsável:** aji-rag + aji-legal
- **Prazo:** Semana 5-6

### ADR-013: Estratégia de cache de respostas
- **Status:** Pendente
- **Opções:** (a) Cache por query hash, (b) Cache semântico, (c) Sem cache
- **Contexto:** Muitas perguntas são repetitivas (FAQ trabalhista). Cache reduz custo mas pode servir resposta desatualizada.
- **Agente responsável:** aji-architect
- **Prazo:** Semana 5-6

### ADR-014: Monitoramento de qualidade das respostas
- **Status:** Pendente
- **Opções:** (a) Feedback do usuário (thumbs up/down), (b) LLM-as-judge, (c) Ambos
- **Contexto:** Essencial para medir a North Star (satisfação ≥ 4/5)
- **Agente responsável:** aji-product
- **Prazo:** Semana 7

---

*Última atualização: Março 2026*
*Para adicionar uma decisão: copie o template de uma ADR existente e incremente o número.*
