"""
Seleção de modelo OpenAI baseada em complexidade da query.

Decisão tomada (CLAUDE.md seção 4):
- gpt-4o-mini: 90% das consultas (simples, FAQ, fluxos guiados)
- gpt-4o: 10% dos casos (alta complexidade, score > 0.75)

Não alterar os modelos sem revisar ADR-002.
"""

import re

# Palavras-chave que indicam alta complexidade jurídica —
# situações que tipicamente exigem raciocínio jurídico mais profundo
# ou envolvem risco judicial real.
COMPLEX_KEYWORDS: list[str] = [
    "processo",
    "ação judicial",
    "recurso",
    "petição",
    "litígio",
    "indenização",
    "rescisão indireta",
    "dano moral",
    "trabalhista grave",
    "falência",
    "recuperação judicial",
    "crime",
    "penal",
    "criminal",
    "fraude",
    "estelionato",
    "mandado",
    "liminar",
    "tutela",
    "audiência",
    "vara do trabalho",
    "tribunal",
    "TRT",
    "TST",
    "STJ",
    "STF",
]

# Compilar regex para busca case-insensitive eficiente
_COMPLEX_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in COMPLEX_KEYWORDS),
    re.IGNORECASE,
)

MODEL_SIMPLE = "gpt-4o-mini"
MODEL_COMPLEX = "gpt-4o"
COMPLEXITY_THRESHOLD = 0.75


def compute_complexity_score(query: str) -> float:
    """
    Calcula score de complexidade da query entre 0.0 e 1.0.

    Componentes:
    - Palavras-chave complexas (peso 0.6): presença de termos jurídicos de alto risco
    - Comprimento (peso 0.2): queries longas (>200 chars) tendem a ser mais complexas
    - Múltiplas perguntas (peso 0.2): encadeamento de perguntas indica complexidade

    Args:
        query: Texto da pergunta do usuário.

    Returns:
        Float entre 0.0 (simples) e 1.0 (máxima complexidade).
    """
    query = query.strip()
    if not query:
        return 0.0

    # Componente 1: palavras-chave complexas (peso 0.6)
    matches = _COMPLEX_PATTERN.findall(query)
    # Até 3 keywords = score máximo para este componente
    keyword_score = min(len(matches) / 3.0, 1.0) * 0.6

    # Componente 2: comprimento da query (peso 0.2)
    # Queries com >200 chars recebem score máximo neste componente
    length_score = min(len(query) / 200.0, 1.0) * 0.2

    # Componente 3: múltiplas perguntas encadeadas (peso 0.2)
    # Conta ocorrências de "?" como proxy para perguntas encadeadas
    question_count = query.count("?")
    multi_question_score = min(question_count / 3.0, 1.0) * 0.2

    return round(keyword_score + length_score + multi_question_score, 4)


def select_model(query: str) -> str:
    """
    Seleciona o modelo OpenAI adequado para a query.

    complexity_score > COMPLEXITY_THRESHOLD (0.75) → gpt-4o
    caso contrário → gpt-4o-mini

    Args:
        query: Texto da pergunta do usuário.

    Returns:
        String com o nome do modelo: "gpt-4o" ou "gpt-4o-mini".
    """
    score = compute_complexity_score(query)
    return MODEL_COMPLEX if score > COMPLEXITY_THRESHOLD else MODEL_SIMPLE
