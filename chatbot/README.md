# AJI — Assistente Jurídico Inteligente (Chatbot Local)

Chatbot de orientação jurídica para empresários brasileiros de PMEs, com base de conhecimento em legislação brasileira (9 PDFs) e rejeição educada de perguntas fora do escopo.

## Pré-requisitos

- **Python 3.10+** instalado ([download](https://www.python.org/downloads/))
- **Conta Groq** gratuita com API key ([criar aqui](https://console.groq.com/keys))

## Instalação (Windows)

### 1. Abra o terminal (PowerShell ou CMD) e navegue até a pasta do projeto

```powershell
cd "caminho\para\aji-chatbot"
```

### 2. Crie um ambiente virtual (recomendado)

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Instale as dependências

```powershell
pip install -r requirements.txt
```

### 4. Configure a API key do Groq

Crie um arquivo `.env` na raiz do projeto (ou defina a variável de ambiente):

```powershell
# Opção 1: Criar arquivo .env
echo GROQ_API_KEY=sua_chave_aqui > .env

# Opção 2: Definir variável de ambiente (temporário)
$env:GROQ_API_KEY="sua_chave_aqui"
```

### 5. Ingira os PDFs na base de conhecimento (apenas na primeira vez)

```powershell
python ingest.py
```

Isso processa os 9 PDFs da pasta `knowledge_base/` e cria a base vetorial em `chroma_db/`. Leva ~2-5 minutos dependendo do hardware.

### 6. Inicie o chatbot

```powershell
python app.py
```

### 7. Acesse no navegador

Abra: **http://localhost:8080**

---

## Instalação (Linux/Mac)

```bash
cd aji-chatbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export GROQ_API_KEY="sua_chave_aqui"
python ingest.py   # apenas primeira vez
python app.py
# Acesse: http://localhost:8080
```

---

## Estrutura do Projeto

```
aji-chatbot/
├── app.py                  ← Backend FastAPI + Groq + RAG
├── ingest.py               ← Script de ingestão dos PDFs
├── requirements.txt        ← Dependências Python
├── README.md               ← Este arquivo
├── .env                    ← API key (criar manualmente)
├── knowledge_base/         ← 9 PDFs de legislação brasileira
│   ├── cdc_e_normas_correlatas_2ed.pdf
│   ├── Código Civil 2 ed.pdf
│   ├── Enunciados_Sumulas_STF_1_a_736_Completo.pdf
│   ├── Enunciados_Sumula_Camara_Civel.pdf
│   ├── lei-8245-18-outubro-1991-322506-normaatualizada-pl.pdf
│   ├── Lei-Nro-9492.pdf
│   ├── Lei_geral_protecao_dados_pessoais_1ed.pdf
│   ├── Sumulas STJ.pdf
│   └── Todos os enunciados - ate 89 - FEVEREIRO 2026.pdf
├── chroma_db/              ← Base vetorial (gerada pelo ingest.py)
└── static/
    └── index.html          ← Interface web do chatbot
```

## Tecnologias

| Componente | Tecnologia |
|-----------|-----------|
| Backend | FastAPI (Python) |
| LLM | Groq (Llama 3.3 70B) — gratuito |
| RAG | ChromaDB (vetorial local) |
| Embeddings | all-MiniLM-L6-v2 (local, sem API) |
| Frontend | HTML + CSS + JavaScript (vanilla) |
| Extração PDF | PyPDF2 |

## Comandos Úteis

```bash
# Iniciar o chatbot
python app.py

# Re-ingerir os PDFs (se adicionar novos)
python ingest.py

# Ver estatísticas da base
curl http://localhost:8080/api/stats

# Limpar histórico de conversa
curl -X POST http://localhost:8080/api/clear
```

## Adicionar Novos PDFs

1. Coloque o PDF na pasta `knowledge_base/`
2. Execute `python ingest.py` novamente
3. Reinicie o chatbot com `python app.py`

## Trocar o Modelo LLM

No arquivo `app.py`, altere a variável `MODEL_NAME`:

```python
# Opções Groq (gratuitas):
MODEL_NAME = "llama-3.3-70b-versatile"    # Melhor qualidade
MODEL_NAME = "llama-3.1-8b-instant"       # Mais rápido
MODEL_NAME = "mixtral-8x7b-32768"         # Bom equilíbrio
```
