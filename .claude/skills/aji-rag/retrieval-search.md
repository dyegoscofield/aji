# Busca Semântica & Retrieval

## Configuração

```python
# services/rag/retrieval.py

class LegalRetriever:
    TOP_K = 6                    # Número de chunks recuperados
    SIMILARITY_THRESHOLD = 0.72  # Mínimo de similaridade (cosine)
```

## Busca em Duas Camadas

```python
    def retrieve(self, query: str, tenant_id: str) -> list[dict]:
        """
        Busca em duas camadas:
        1. Base global (leis, CLT, CDC, contratos padrão)
        2. Base privada do tenant (se plano Personalizado)
        """
        query_embedding = self.embedder.embed_query(query)
        
        # Query pgvector com cosine similarity
        results = self.db.execute("""
            SELECT content, metadata, 
                   1 - (embedding <=> %s::vector) as similarity
            FROM legal_chunks
            WHERE (tenant_id IS NULL OR tenant_id = %s)
              AND 1 - (embedding <=> %s::vector) > %s
            ORDER BY similarity DESC
            LIMIT %s
        """, [query_embedding, tenant_id, query_embedding, 
               self.SIMILARITY_THRESHOLD, self.TOP_K])
        
        return self._rerank(query, results)
```

## Reranking

```python
    def _rerank(self, query: str, results: list) -> list:
        """
        Reranking simples por relevância temática.
        Para produção: usar cross-encoder (ms-marco-MiniLM)
        """
        # Por ora: ordenar por similarity score já é suficiente
        return sorted(results, key=lambda x: x['similarity'], reverse=True)
```

## Estrutura da Base no pgvector

```
knowledge_base/
├── global/                    # Disponível para todos os tenants
│   ├── legislacao/            # Leis (CLT, CDC, LGPD, CC)
│   ├── fluxos/                # Passo a passo (demissão, cobrança, etc.)
│   ├── modelos/               # Templates de documentos
│   └── faq/                   # Perguntas frequentes por área
└── tenant_{uuid}/             # Base privada (plano Personalizado)
    ├── contratos_empresa/
    ├── politicas_internas/
    └── historico_casos/
```

## Regras

1. Toda busca DEVE incluir `tenant_id` no filtro (multi-tenancy)
2. Threshold de 0.72 é o mínimo — abaixo disso, o chunk não é relevante
3. Se nenhum chunk atinge o threshold, o agente deve sinalizar que não tem fonte específica
4. Base privada do tenant só existe no plano Personalizado
