import re
from dataclasses import dataclass

from langchain_core.documents import Document


ARTICLE_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:Artículo|Artículo)\s+(\d+)[\.\°]",
    re.IGNORECASE,
)

ARTICLE_SPLIT_PATTERN = re.compile(
    r"(?=\n\s*(?:Artículo|Artículo)\s+\d+[\.\°])",
    re.IGNORECASE,
)

CHAPTER_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:CAPÍTULO|Capítulo)\s+([IVXLCDM\d]+)[\.\:]?\s*(.*)",
    re.IGNORECASE,
)


@dataclass
class ChunkMetadata:
    documento: str
    capitulo: str | None = None
    articulo: str | None = None
    page: int | None = None


def _extract_chapter(text: str) -> str | None:
    match = CHAPTER_PATTERN.search(text)
    if match:
        num, title = match.group(1), match.group(2).strip()
        return f"Capítulo {num}: {title}" if title else f"Capítulo {num}"
    return None


def _extract_article(text: str) -> str | None:
    match = ARTICLE_PATTERN.search(text)
    return match.group(1) if match else None


def _split_by_articles(full_text: str) -> list[str]:
    """Divide el texto en secciones, cada una comenzando con un artículo."""
    raw_sections = ARTICLE_SPLIT_PATTERN.split(full_text)
    return [s.strip() for s in raw_sections if s.strip()]


def _split_long_section(section: str, max_size: int, overlap: int) -> list[str]:
    """Divide una sección larga manteniendo el inicio del artículo."""
    if len(section) <= max_size:
        return [section]

    # Encontrar dónde termina el header del artículo
    article_match = ARTICLE_PATTERN.search(section)
    if not article_match:
        # No hay artículo, dividir por párrafos
        return _split_by_paragraphs(section, max_size, overlap)

    # Obtener el header del artículo (todo hasta el primer párrafo)
    end_of_header = section.find("\n\n", article_match.end())
    if end_of_header == -1:
        end_of_header = len(section)

    header = section[:end_of_header].strip()
    body = section[end_of_header:].strip()

    if not body:
        return [section]

    # Dividir el cuerpo por párrafos
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = header

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_size:
            current_chunk += "\n\n" + para
        else:
            chunks.append(current_chunk)
            # Iniciar nuevo chunk con header para contexto
            current_chunk = header + "\n\n[continúa...]\n\n" + para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _split_by_paragraphs(text: str, max_size: int, overlap: int) -> list[str]:
    """Divide texto por párrafos cuando no hay estructura de artículo."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_size:
            current += "\n\n" + para if current else para
        else:
            if current:
                chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    return chunks


def split_regulatory_document(
    pages: list[Document],
    documento: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    """Divide un documento normativo en chunks, cada uno comenzando con su artículo.

    Args:
        pages: Páginas del documento cargadas con PyPDFLoader.
        documento: Identificador del documento ("pregrado" o "posgrado").
        chunk_size: Tamaño máximo de cada chunk en caracteres.
        chunk_overlap: Solapamiento entre chunks consecutivos.

    Returns:
        Lista de Document con metadata enriquecida.
    """
    full_text = "\n\n".join(page.page_content for page in pages)
    page_map = _build_page_map(pages)

    # Paso 1: Dividir por artículos
    sections = _split_by_articles(full_text)

    # Paso 2: Dividir secciones largas manteniendo header del artículo
    chunks = []
    for section in sections:
        sub_chunks = _split_long_section(section, chunk_size, chunk_overlap)
        chunks.extend(sub_chunks)

    # Paso 3: Crear Documents con metadata
    documents = []
    for chunk_text in chunks:
        capitulo = _extract_chapter(chunk_text)
        articulo = _extract_article(chunk_text)
        page = _find_page(chunk_text, page_map)

        metadata = ChunkMetadata(
            documento=documento,
            capitulo=capitulo,
            articulo=articulo,
            page=page,
        )

        documents.append(
            Document(
                page_content=chunk_text.strip(),
                metadata=metadata.__dict__,
            )
        )

    return documents


def _build_page_map(pages: list[Document]) -> list[tuple[str, int]]:
    """Construye una lista de (texto_pagina, numero_pagina)."""
    result = []
    for i, page in enumerate(pages):
        result.append((page.page_content, i + 1))
    return result


def _find_page(chunk_text: str, page_map: list[tuple[str, int]]) -> int | None:
    """Estima la página basándose en el inicio del chunk."""
    chunk_start = chunk_text[:200]
    for page_content, page_num in page_map:
        if chunk_start[:50] in page_content:
            return page_num
    return None
