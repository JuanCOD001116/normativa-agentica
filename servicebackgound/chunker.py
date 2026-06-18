import io
import re
from dataclasses import dataclass

import pypdf

ARTICLE_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:Art[ií]culo)\s+(\d+)[\.\°]",
    re.IGNORECASE,
)

ARTICLE_SPLIT_PATTERN = re.compile(
    r"(?=\n\s*(?:Art[ií]culo)\s+\d+[\.\°])",
    re.IGNORECASE,
)

CHAPTER_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:CAP[IÍ]TULO|Cap[ií]tulo)\s+([IVXLCDM\d]+)[\.\:]?\s*(.*)",
    re.IGNORECASE,
)


@dataclass
class Chunk:
    text: str
    articulo: str | None = None
    capitulo: str | None = None
    page: int | None = None


def _extract_pages(pdf_bytes: bytes) -> list[tuple[str, int]]:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return [(page.extract_text() or "", i + 1) for i, page in enumerate(reader.pages)]


def _extract_article(text: str) -> str | None:
    match = ARTICLE_PATTERN.search(text)
    return match.group(1) if match else None


def _extract_chapter(text: str) -> str | None:
    match = CHAPTER_PATTERN.search(text)
    if match:
        num, title = match.group(1), match.group(2).strip()
        return f"Capítulo {num}: {title}" if title else f"Capítulo {num}"
    return None


def _find_page(chunk_text: str, page_map: list[tuple[str, int]]) -> int | None:
    snippet = chunk_text[:50]
    for page_text, page_num in page_map:
        if snippet in page_text:
            return page_num
    return None


def _split_by_articles(full_text: str) -> list[str]:
    raw = ARTICLE_SPLIT_PATTERN.split(full_text)
    return [s.strip() for s in raw if s.strip()]


def _split_by_paragraphs(text: str, max_size: int) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
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


def _split_long_section(section: str, max_size: int) -> list[str]:
    if len(section) <= max_size:
        return [section]

    article_match = ARTICLE_PATTERN.search(section)
    if not article_match:
        return _split_by_paragraphs(section, max_size)

    end_of_header = section.find("\n\n", article_match.end())
    if end_of_header == -1:
        end_of_header = len(section)

    header = section[:end_of_header].strip()
    body = section[end_of_header:].strip()

    if not body:
        return [section]

    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current_chunk = header

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_size:
            current_chunk += "\n\n" + para
        else:
            chunks.append(current_chunk)
            current_chunk = header + "\n\n[continúa...]\n\n" + para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def chunk_pdf(pdf_bytes: bytes, chunk_size: int = 1000) -> list[Chunk]:
    """Divide un PDF en chunks por artículo con metadata de articulo, capitulo y page."""
    page_map = _extract_pages(pdf_bytes)
    full_text = "\n\n".join(text for text, _ in page_map)

    if not full_text.strip():
        return []

    chunks: list[Chunk] = []
    for section in _split_by_articles(full_text):
        for text in _split_long_section(section, chunk_size):
            chunks.append(
                Chunk(
                    text=text,
                    articulo=_extract_article(text),
                    capitulo=_extract_chapter(text),
                    page=_find_page(text, page_map),
                )
            )

    return chunks
