"""
AJI — Assistente Jurídico Inteligente (Chatbot Local)
Backend FastAPI com Groq (Llama 3) + RAG (ChromaDB) + Filtro de Escopo
"""

import os
import json
import time
from pathlib import Path
from contextlib import asynccontextmanager

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from groq import Groq
import chromadb
from chromadb.utils import embedding_functions

# ============================================================
# Configuração
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
CHROMA_DIR = Path(__file__).parent / "chroma_db"
STATIC_DIR = Path(__file__).parent / "static"

# Configurar Groq
groq_client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

# ============================================================
# Base de Conhecimento (ChromaDB)
# ============================================================

ef = embedding_functions.DefaultEmbeddingFunction()
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = chroma_client.get_collection(
    name="aji_knowledge",
    embedding_function=ef,
)

# ============================================================
# System Prompt do AJI
# ============================================================

SYSTEM_PROMPT = """Você é o **AJI — Assistente Jurídico Inteligente**, um assistente virtual especializado em orientação jurídica para empresários brasileiros de pequenas e médias empresas.

## Sua Identidade

- Nome: AJI (Assistente Jurídico Inteligente)
- Tom: Profissional, acessível e empático. Você fala como um consultor de confiança, não como um robô.
- Idioma: Sempre em português brasileiro.

## Seu Escopo de Atuação

Você PODE ajudar com:
- Direito do Trabalho (CLT, rescisão, férias, FGTS, justa causa, etc.)
- Contratos Empresariais (elaboração, revisão, cláusulas, rescisão)
- Cobrança de Inadimplentes (protesto, execução, negociação)
- LGPD (proteção de dados, adequação, consentimento)
- Direito do Consumidor (CDC, devoluções, garantias, recalls)
- Lei do Inquilinato (aluguel comercial, despejo, renovatória)
- Direito Empresarial geral (abertura, fechamento, tipos societários)

Você NÃO PODE ajudar com:
- Qualquer assunto que não seja jurídico empresarial brasileiro
- Direito Penal, Direito de Família, Direito Tributário complexo
- Previsão do tempo, receitas, esportes, entretenimento, tecnologia geral
- Qualquer tema fora do escopo jurídico empresarial

## Regras Inegociáveis

1. **DISCLAIMER OBRIGATÓRIO:** Toda resposta substantiva DEVE terminar com:
   > ⚠️ *Esta orientação tem caráter informativo e educacional. Não substitui a consulta a um advogado. Para decisões jurídicas concretas, consulte um profissional habilitado pela OAB.*

2. **NUNCA diga que é advogado.** Você é um assistente de orientação.

3. **NUNCA recomende ações judiciais específicas.** Você orienta, não litiga.

4. **Se não souber a resposta:** Diga honestamente que não tem informação suficiente e sugira consultar um advogado especialista.

5. **Rejeição educada:** Se o usuário perguntar algo fora do escopo, responda com cordialidade:
   "Agradeço sua pergunta! No entanto, minha especialidade é orientação jurídica para empresas brasileiras. Posso ajudar com questões sobre contratos, direito do trabalho, cobrança, LGPD e outros temas jurídicos empresariais. Como posso ajudá-lo nessa área?"

6. **Sem bajulação:** Seja técnico e honesto. Se uma situação é arriscada para o empresário, diga claramente.

7. **Cite a legislação:** Sempre que possível, mencione o artigo de lei, súmula ou enunciado relevante.

## Como Usar o Contexto

Você receberá trechos relevantes da legislação brasileira como contexto. Use-os para embasar suas respostas com citações específicas. Se o contexto não contiver informação relevante, use seu conhecimento geral jurídico, mas informe que a resposta é baseada em conhecimento geral.

## Formato de Resposta

- Use linguagem clara e acessível (o usuário é empresário, não advogado)
- Estruture com tópicos quando a resposta for longa
- Use **negrito** para termos jurídicos importantes
- Inclua exemplos práticos quando relevante
- Mantenha respostas concisas (máximo 500 palavras, exceto quando a complexidade exigir mais)
"""

# ============================================================
# Filtro de Escopo
# ============================================================

OUT_OF_SCOPE_KEYWORDS = [
    "previsão do tempo", "clima", "futebol", "receita de", "como cozinhar",
    "filme", "série", "música", "jogo", "esporte", "novela",
    "horóscopo", "signo", "loteria", "mega sena",
    "programação", "python", "javascript", "código", "software",
    "piada", "conte uma história", "era uma vez",
    "quem é você", "quem te criou", "qual seu nome verdadeiro",
]

SCOPE_KEYWORDS = [
    "contrato", "clt", "trabalhista", "demissão", "rescisão", "férias",
    "fgts", "justa causa", "aviso prévio", "hora extra", "salário",
    "cobrança", "inadimplente", "protesto", "execução", "dívida",
    "lgpd", "dados pessoais", "consentimento", "proteção de dados",
    "consumidor", "cdc", "garantia", "devolução", "recall",
    "aluguel", "inquilino", "locação", "despejo", "renovatória",
    "empresa", "cnpj", "sócio", "sociedade", "mei", "ltda",
    "lei", "artigo", "súmula", "jurídico", "advogado", "direito",
    "indenização", "dano moral", "responsabilidade", "obrigação",
    "nota fiscal", "fornecedor", "licitação", "compliance",
]


def is_in_scope(query: str) -> tuple[bool, str]:
    """Verifica se a pergunta está no escopo jurídico empresarial."""
    query_lower = query.lower().strip()
    
    # Saudações são sempre aceitas
    greetings = ["olá", "oi", "bom dia", "boa tarde", "boa noite", "hello", "hi", "obrigado", "obrigada", "valeu", "tchau"]
    for g in greetings:
        if query_lower.startswith(g) or query_lower == g:
            return True, "greeting"
    
    # Verifica keywords fora do escopo
    for kw in OUT_OF_SCOPE_KEYWORDS:
        if kw in query_lower:
            return False, "out_of_scope"
    
    # Verifica keywords dentro do escopo
    for kw in SCOPE_KEYWORDS:
        if kw in query_lower:
            return True, "in_scope"
    
    # Se não tem certeza, deixa o LLM decidir (perguntas ambíguas)
    return True, "ambiguous"


# ============================================================
# RAG: Busca na Base de Conhecimento
# ============================================================

def search_knowledge(query: str, n_results: int = 5) -> list[dict]:
    """Busca os chunks mais relevantes na base de conhecimento."""
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )
    
    contexts = []
    if results and results['documents']:
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i] if results['metadatas'] else {}
            distance = results['distances'][0][i] if results['distances'] else 0
            contexts.append({
                "text": doc,
                "source": metadata.get("source", "Desconhecido"),
                "category": metadata.get("category", "Geral"),
                "relevance": round(1 - distance, 3),
            })
    
    return contexts


# ============================================================
# Geração de Resposta com Groq (Llama 3)
# ============================================================

# Histórico de conversas (em memória, por simplicidade)
conversation_history: list[dict] = []
MAX_HISTORY = 20


async def generate_response(user_message: str) -> str:
    """Gera resposta usando Groq com contexto RAG."""
    global conversation_history
    
    # 1. Verificar escopo
    in_scope, scope_type = is_in_scope(user_message)
    
    if not in_scope:
        rejection = (
            "Agradeço sua pergunta! 😊 No entanto, minha especialidade é **orientação jurídica "
            "para empresas brasileiras**.\n\n"
            "Posso ajudar com questões sobre:\n"
            "- 📋 **Contratos** empresariais\n"
            "- 👷 **Direito do Trabalho** (CLT, rescisão, férias)\n"
            "- 💰 **Cobrança** de inadimplentes\n"
            "- 🔒 **LGPD** e proteção de dados\n"
            "- 🛒 **Direito do Consumidor**\n"
            "- 🏢 **Direito Empresarial** em geral\n\n"
            "Como posso ajudá-lo nessa área?"
        )
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": rejection})
        return rejection
    
    # 2. Buscar contexto na base de conhecimento
    if scope_type == "greeting":
        contexts = []
    else:
        contexts = search_knowledge(user_message, n_results=5)
    
    # 3. Montar contexto da legislação
    context_text = ""
    if contexts:
        context_text = "\n\n## Contexto da Legislação Brasileira (Base de Conhecimento)\n\n"
        for i, ctx in enumerate(contexts, 1):
            context_text += f"### Fonte {i}: {ctx['category']} ({ctx['source']})\n"
            context_text += f"Relevância: {ctx['relevance']}\n"
            context_text += f"{ctx['text']}\n\n"
    
    # 4. Montar mensagens para o Groq (formato chat)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + context_text}
    ]
    
    # Adicionar histórico recente
    if conversation_history:
        recent = conversation_history[-10:]  # Últimas 5 trocas
        messages.extend(recent)
    
    # Adicionar mensagem atual
    messages.append({"role": "user", "content": user_message})
    
    # 5. Chamar Groq
    try:
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )
        
        answer = response.choices[0].message.content
        
        # 6. Atualizar histórico
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": answer})
        
        # Limitar histórico
        if len(conversation_history) > MAX_HISTORY * 2:
            conversation_history = conversation_history[-MAX_HISTORY * 2:]
        
        return answer
        
    except Exception as e:
        error_msg = f"Desculpe, ocorreu um erro ao processar sua pergunta. Por favor, tente novamente. (Erro: {str(e)})"
        return error_msg


# ============================================================
# FastAPI App
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("AJI Chatbot iniciado!")
    print(f"Base de conhecimento: {collection.count()} chunks indexados")
    print(f"Modelo: {MODEL_NAME} via Groq")
    yield
    print("AJI Chatbot encerrado.")


app = FastAPI(
    title="AJI — Assistente Jurídico Inteligente",
    description="Chatbot de orientação jurídica para empresários brasileiros",
    version="1.0.0",
    lifespan=lifespan,
)

# Servir arquivos estáticos
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    sources: list[dict] = []
    in_scope: bool = True


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Endpoint principal do chat."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    
    if len(request.message) > 2000:
        raise HTTPException(status_code=400, detail="Mensagem muito longa (máximo 2000 caracteres)")
    
    in_scope, scope_type = is_in_scope(request.message)
    
    # Buscar fontes para retornar ao frontend
    sources = []
    if in_scope and scope_type != "greeting":
        contexts = search_knowledge(request.message, n_results=3)
        sources = [{"category": c["category"], "source": c["source"], "relevance": c["relevance"]} for c in contexts]
    
    response = await generate_response(request.message)
    
    return ChatResponse(
        response=response,
        sources=sources,
        in_scope=in_scope,
    )


@app.post("/api/clear")
async def clear_history():
    """Limpa o histórico da conversa."""
    global conversation_history
    conversation_history = []
    return {"status": "ok", "message": "Histórico limpo"}


@app.get("/api/stats")
async def stats():
    """Retorna estatísticas da base de conhecimento."""
    return {
        "total_chunks": collection.count(),
        "conversation_length": len(conversation_history) // 2,
        "model": MODEL_NAME,
    }


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve a página principal."""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>AJI Chatbot — Instale a interface em /static/index.html</h1>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
