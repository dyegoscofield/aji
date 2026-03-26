# Skill: AJI RAG & IA Jurídica

Recursos de referência para o agente aji-rag. Carregue sob demanda conforme a tarefa.

## Recursos Disponíveis

| Recurso | Arquivo | Quando Carregar |
|---------|---------|-----------------|
| System Prompt Jurídico | `system-prompt.md` | Ao ajustar o prompt do AJI, formato de resposta, tom |
| Pipeline de Ingestão | `ingestion-pipeline.md` | Ao processar documentos, chunking, embeddings |
| Busca Semântica | `retrieval-search.md` | Ao ajustar busca, reranking, threshold, top_k |
| Qualidade e Guardrails | `quality-guardrails.md` | Ao avaliar respostas, alucinações, testes de qualidade |

## Base de Conhecimento Jurídico (RAG Source)

A pasta `.claude/base conhecimento/` contém os PDFs de legislação e jurisprudência que alimentam o RAG:

| Documento | Conteúdo | Prioridade para Ingestão |
|-----------|----------|-------------------------|
| `cdc_e_normas_correlatas_2ed.pdf` | Código de Defesa do Consumidor + normas correlatas | Alta — área de cobertura do AJI |
| `Código Civil 2 ed.pdf` | Código Civil completo (contratos, obrigações) | Alta — contratos empresariais |
| `Lei_geral_protecao_dados_pessoais_1ed.pdf` | LGPD completa | Alta — área de cobertura do AJI |
| `lei-8245-18-outubro-1991-322506-normaatualizada-pl.pdf` | Lei do Inquilinato (8.245/91) | Média — relevante para empresas com imóveis |
| `Lei-Nro-9492.pdf` | Lei de Protesto (9.492/97) | Média — cobrança e inadimplência |
| `Enunciados_Sumulas_STF_1_a_736_Completo.pdf` | Todas as súmulas do STF (1 a 736) | Alta — jurisprudência consolidada |
| `Sumulas STJ.pdf` | Súmulas do STJ | Alta — jurisprudência consolidada |
| `Enunciados_Sumula_Camara_Civel.pdf` | Súmulas da Câmara Cível | Média — jurisprudência estadual |
| `Todos os enunciados - ate 89 - FEVEREIRO 2026.pdf` | Enunciados atualizados até fev/2026 | Alta — mais recente disponível |

### Observação sobre a CLT

A CLT (Consolidação das Leis do Trabalho) **não está na base de conhecimento ainda**. Como Direito do Trabalho é a área #1 de cobertura do AJI, a inclusão da CLT consolidada é **prioridade máxima** para completar a base.

## Regra de Carregamento

Leia apenas o recurso necessário para a tarefa atual. Não carregue todos de uma vez. A base de conhecimento em PDF é para referência do pipeline de ingestão — não tente ler os PDFs diretamente durante uma sessão de desenvolvimento.
