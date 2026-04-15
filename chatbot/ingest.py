"""
AJI — Ingestão de PDFs para Base de Conhecimento (Versão Incremental)
Extrai texto dos PDFs, chunka e indexa no ChromaDB com embeddings locais.
Agora verifica se o arquivo já foi processado para evitar duplicidade.
"""

import os
import re
import hashlib
from pathlib import Path
from PyPDF2 import PdfReader
import chromadb
from chromadb.utils import embedding_functions

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge_base"
CHROMA_DIR = Path(__file__).parent / "chroma_db"

# Mapeamento de PDFs para categorias
PDF_CATEGORIES = {
    "cdc": "Código de Defesa do Consumidor",
    "Código Civil": "Código Civil Brasileiro",
    "Sumulas_STF": "Súmulas do STF",
    "Sumula_Camara": "Súmulas da Câmara Cível",
    "lei-8245": "Lei do Inquilinato (Lei 8.245/91)",
    "Lei-Nro-9492": "Lei de Protesto (Lei 9.492/97)",
    "Lei_geral_protecao": "LGPD (Lei 13.709/2018)",
    "Sumulas STJ": "Súmulas do STJ",
    "enunciados": "Enunciados Consolidados",
}


def classify_pdf(filename: str) -> str:
    """Classifica o PDF pela categoria baseado no nome do arquivo."""
    for key, category in PDF_CATEGORIES.items():
        if key.lower() in filename.lower():
            return category
    return "Legislação Geral"


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extrai texto de um PDF."""
    reader = PdfReader(str(pdf_path))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def clean_text(text: str) -> str:
    """Limpa o texto extraído."""
    # Remove múltiplas quebras de linha
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove espaços excessivos
    text = re.sub(r' {2,}', ' ', text)
    # Remove caracteres de controle
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Divide o texto em chunks com overlap."""
    chunks = []
    # Tenta dividir por parágrafos primeiro
    paragraphs = text.split('\n\n')
    
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Se o parágrafo é maior que chunk_size, divide por sentenças
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) < chunk_size:
                        current_chunk += sent + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sent + " "
            else:
                current_chunk = para + "\n\n"
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Filtra chunks muito pequenos
    chunks = [c for c in chunks if len(c) > 50]
    
    return chunks


def get_processed_files(collection) -> set:
    """Retorna um conjunto de nomes de arquivos já processados na coleção."""
    try:
        # Busca metadados de todos os documentos (limitado a um campo específico para performance)
        results = collection.get(include=['metadatas'])
        if results and results['metadatas']:
            return {m.get('source') for m in results['metadatas'] if m.get('source')}
    except Exception as e:
        print(f"Erro ao buscar arquivos processados: {e}")
    return set()


def ingest(force_rebuild: bool = False):
    """Processa PDFs e indexa no ChromaDB de forma incremental."""
    print("=" * 60)
    print("AJI — Ingestão de Base de Conhecimento (Incremental)")
    print("=" * 60)
    
    # Inicializa ChromaDB com embeddings locais
    ef = embedding_functions.DefaultEmbeddingFunction()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    if force_rebuild:
        print("\nAVISO: Recriando base de dados do zero...")
        try:
            client.delete_collection("aji_knowledge")
        except:
            pass
    
    # Obtém ou cria a collection
    collection = client.get_or_create_collection(
        name="aji_knowledge",
        embedding_function=ef,
        metadata={"description": "Base de conhecimento jurídico do AJI"}
    )
    
    # Verifica arquivos já processados
    processed_files = get_processed_files(collection) if not force_rebuild else set()
    if processed_files:
        print(f"Arquivos já indexados: {len(processed_files)}")
    
    pdf_files = list(KNOWLEDGE_DIR.glob("*.pdf"))
    
    # Filtra apenas os arquivos que ainda não foram processados
    files_to_process = [f for f in pdf_files if f.name not in processed_files]
    
    if not files_to_process:
        print("\nNenhum arquivo novo encontrado para processar.")
        print("=" * 60)
        return

    print(f"\nEncontrados {len(files_to_process)} novos PDFs para processar.\n")
    
    total_chunks = 0
    
    for pdf_path in files_to_process:
        category = classify_pdf(pdf_path.name)
        print(f"Processando: {pdf_path.name}")
        print(f"  Categoria: {category}")
        
        # Extrai texto
        try:
            text = extract_text_from_pdf(pdf_path)
            text = clean_text(text)
            print(f"  Texto extraído: {len(text)} caracteres")
            
            if len(text) < 100:
                print(f"  AVISO: Texto muito curto, pulando.")
                continue
            
            # Chunka
            chunks = chunk_text(text)
            print(f"  Chunks gerados: {len(chunks)}")
            
            # Indexa
            ids = []
            documents = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                # ID único baseado no nome do arquivo e índice do chunk
                chunk_id = hashlib.md5(f"{pdf_path.name}_{i}".encode()).hexdigest()
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append({
                    "source": pdf_path.name,
                    "category": category,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                })
            
            # ChromaDB aceita batches
            batch_size = 500
            for j in range(0, len(ids), batch_size):
                collection.add(
                    ids=ids[j:j+batch_size],
                    documents=documents[j:j+batch_size],
                    metadatas=metadatas[j:j+batch_size],
                )
            
            total_chunks += len(chunks)
            print(f"  Indexado com sucesso.\n")
        except Exception as e:
            print(f"  ERRO ao processar {pdf_path.name}: {e}")
    
    print("=" * 60)
    print(f"Ingestão completa!")
    print(f"  Novos PDFs processados: {len(files_to_process)}")
    print(f"  Total de novos chunks: {total_chunks}")
    print(f"  Total de chunks na base: {collection.count()}")
    print("=" * 60)


if __name__ == "__main__":
    # Para recriar do zero, use: ingest(force_rebuild=True)
    ingest()
