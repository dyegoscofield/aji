"""
Chunker de documentos Markdown jurídicos.

Estratégia (ADR-003): chunking por seções Markdown, preservando o header
para contexto. Se uma seção exceder max_chars, divide por parágrafo.

Tamanhos definidos em ADR-003:
    lei / faq        → 800 chars (artigos curtos e independentes)
    contrato         → 1200 chars (cláusulas precisam de mais contexto)
    doutrina / fluxo → 1500 chars (explicações precisam de mais contexto)
    sumula           → 400 chars  (enunciados são independentes por natureza)
"""

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    content: str
    source_file: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


# Mapa de tipo de documento → max_chars (ADR-003)
CHUNK_SIZE_BY_DOC_TYPE: dict[str, int] = {
    "lei": 800,
    "faq": 800,
    "contrato": 1200,
    "doutrina": 1500,
    "fluxo": 1500,
    "sumula": 400,
    "enunciado": 500,
}

# Detecta headers Markdown ## ou ###
_HEADER_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


def _infer_doc_type(source_file: str) -> str:
    """Infere o tipo de documento a partir do caminho do arquivo."""
    lower = source_file.lower()
    if "/faq/" in lower or "faq" in lower:
        return "faq"
    if "/sumulas/" in lower or "sumula" in lower:
        return "sumula"
    if "/legislacao/" in lower or "lei" in lower or "clt" in lower or "cdc" in lower:
        return "lei"
    if "/modelos/" in lower or "modelo" in lower or "contrato" in lower:
        return "contrato"
    if "/fluxos/" in lower or "fluxo" in lower or "advertencia" in lower or "demissao" in lower:
        return "fluxo"
    return "doutrina"


def _split_by_paragraphs(text: str, max_chars: int) -> list[str]:
    """Divide texto em parágrafos respeitando max_chars."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
            # Se o parágrafo em si é maior que max_chars, divide na força
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i : i + max_chars])
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


def chunk_markdown(
    content: str,
    source_file: str,
    max_chars: int | None = None,
    doc_type: str | None = None,
) -> list[Chunk]:
    """
    Divide um documento Markdown em chunks semânticos por seção (headers).

    Estratégia:
    1. Identifica seções pelos headers # ## ###
    2. Preserva o texto do header no início de cada chunk para contexto
    3. Se a seção exceder max_chars, subdivide por parágrafo
    4. Extrai tópico e área jurídica dos headers para metadata

    Args:
        content:     Texto completo do arquivo Markdown.
        source_file: Caminho relativo do arquivo (ex: "fluxos/demissao.md").
        max_chars:   Tamanho máximo por chunk em caracteres. Se None, usa o
                     padrão baseado no doc_type inferido.
        doc_type:    Tipo do documento. Se None, inferido do source_file.

    Returns:
        Lista de Chunk com content, source_file, chunk_index e metadata.
    """
    if doc_type is None:
        doc_type = _infer_doc_type(source_file)

    if max_chars is None:
        max_chars = CHUNK_SIZE_BY_DOC_TYPE.get(doc_type, 1000)

    # Extrai o nome do arquivo sem extensão para área
    area = source_file.split("/")[-1].replace(".md", "").replace("_", " ")

    # Encontra posições de todos os headers
    matches = list(_HEADER_RE.finditer(content))

    raw_sections: list[tuple[str, str]] = []  # (header_text, body_text)

    if not matches:
        # Documento sem headers — trata tudo como uma seção
        raw_sections = [("", content.strip())]
    else:
        for i, match in enumerate(matches):
            header_text = match.group(0)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            body = content[start:end].strip()
            raw_sections.append((header_text, body))

        # Texto antes do primeiro header (preâmbulo)
        if matches[0].start() > 0:
            preamble = content[: matches[0].start()].strip()
            if preamble:
                raw_sections.insert(0, ("", preamble))

    chunks: list[Chunk] = []
    chunk_index = 0

    for header_text, body in raw_sections:
        # Monta o texto completo da seção com o header como contexto
        section_text = (f"{header_text}\n\n{body}".strip() if header_text else body)

        if not section_text:
            continue

        if len(section_text) <= max_chars:
            sub_chunks = [section_text]
        else:
            # Divide por parágrafo, mas preserva o header em cada sub-chunk
            paragraphs_body = _split_by_paragraphs(body, max_chars - len(header_text) - 2)
            sub_chunks = []
            for para in paragraphs_body:
                text = (f"{header_text}\n\n{para}".strip() if header_text else para)
                sub_chunks.append(text)

        for sub in sub_chunks:
            if not sub.strip():
                continue

            # Extrai tópico do header (remove os # iniciais)
            topic = re.sub(r"^#+\s*", "", header_text).strip() if header_text else area

            chunks.append(
                Chunk(
                    content=sub.strip(),
                    source_file=source_file,
                    chunk_index=chunk_index,
                    metadata={
                        "doc_type": doc_type,
                        "topic": topic,
                        "area": area,
                        "source_file": source_file,
                    },
                )
            )
            chunk_index += 1

    return chunks
