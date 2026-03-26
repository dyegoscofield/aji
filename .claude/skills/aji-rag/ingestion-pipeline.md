# Pipeline de Ingestão de Documentos Jurídicos

## Arquitetura

```
Documento Jurídico (PDF/MD)
      ↓
  Preprocessor (limpeza, metadata extraction)
      ↓
  Chunker (por artigo/cláusula/tema — tamanho diferenciado)
      ↓
  Embedder (OpenAI text-embedding-3-small, 1536 dims)
      ↓
  pgvector (PostgreSQL — tabela legal_chunks)
```

## Estratégia de Chunking (ADR-003)

```python
# services/rag/ingestion.py

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

class LegalDocumentIngester:
    """
    Chunking diferenciado por tipo de documento jurídico.
    Decisão tomada (ADR-003): não rediscutir tamanhos.
    """
    
    CHUNK_SIZES = {
        'lei': 800,          # Artigos de lei: menores, mais precisos
        'contrato': 1200,    # Cláusulas: um pouco maiores
        'doutrina': 1500,    # Explicações: contexto maior
        'faq': 600,          # FAQ: respostas curtas
        'sumula': 400,       # Súmulas: enunciados curtos e independentes
        'enunciado': 500,    # Enunciados de jurisprudência
    }
    CHUNK_OVERLAP = 150

    def __init__(self, doc_type: str = 'doutrina'):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZES[doc_type],
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\nArt.", "\n§", "\nInciso", "\nSúmula", "\n\n", "\n", " "]
        )
        self.embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    
    def ingest(self, text: str, metadata: dict, tenant_id: str = None):
        """
        tenant_id=None: base global compartilhada
        tenant_id=UUID: base privada do tenant (plano Personalizado)
        """
        chunks = self.splitter.split_text(text)
        embeddings = self.embedder.embed_documents(chunks)
        
        for chunk, embedding in zip(chunks, embeddings):
            self._store(chunk, embedding, metadata, tenant_id)
```

## Mapeamento da Base de Conhecimento para Ingestão

| PDF na base | doc_type | Prioridade | Separadores Especiais |
|-------------|----------|------------|----------------------|
| `cdc_e_normas_correlatas_2ed.pdf` | `lei` | Alta | `\nArt.`, `\n§`, `\nInciso` |
| `Código Civil 2 ed.pdf` | `lei` | Alta | `\nArt.`, `\n§` |
| `Lei_geral_protecao_dados_pessoais_1ed.pdf` | `lei` | Alta | `\nArt.`, `\n§` |
| `lei-8245-18-outubro-1991-322506-normaatualizada-pl.pdf` | `lei` | Média | `\nArt.`, `\n§` |
| `Lei-Nro-9492.pdf` | `lei` | Média | `\nArt.` |
| `Enunciados_Sumulas_STF_1_a_736_Completo.pdf` | `sumula` | Alta | `\nSúmula` |
| `Sumulas STJ.pdf` | `sumula` | Alta | `\nSúmula` |
| `Enunciados_Sumula_Camara_Civel.pdf` | `sumula` | Média | `\nSúmula` |
| `Todos os enunciados - ate 89 - FEVEREIRO 2026.pdf` | `enunciado` | Alta | `\nEnunciado` |

## Metadata Obrigatória por Chunk

```python
metadata = {
    "source": "cdc_e_normas_correlatas_2ed.pdf",
    "doc_type": "lei",                    # lei, contrato, doutrina, faq, sumula, enunciado
    "legal_reference": "Art. 12 do CDC",  # Referência legal específica (quando possível)
    "area": "consumidor",                 # trabalhista, contratos, consumidor, lgpd, societario
    "ingested_at": "2026-03-26T00:00:00Z",
    "version": "2ed",
}
```

## Lacuna Identificada

A **CLT (Consolidação das Leis do Trabalho)** não está na base de conhecimento. Como Direito do Trabalho é a área #1 de cobertura do AJI, a inclusão é prioridade máxima. Buscar versão consolidada atualizada para ingestão.
