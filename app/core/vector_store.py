import os
import re
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

from app.core.embeddings import get_embeddings

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

_client = None

ARTICLE_NUMBER_PATTERN = re.compile(r"art[ií]culo\s+(\d+)", re.IGNORECASE)


def _get_client():
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client


def _extract_article_numbers(query: str) -> list[str]:
    """Extrae números de artículo de la query."""
    return ARTICLE_NUMBER_PATTERN.findall(query)


def _fetch_articles_by_number(article_numbers: list[str], documento: str | None = None) -> list[dict]:
    """Busca chunks directamente por número de artículo en metadata."""
    client = _get_client()
    results = []

    for art_num in article_numbers:
        query = client.table("documents").select("*").eq(
            "metadata->>articulo", art_num
        )
        if documento:
            query = query.eq("metadata->>documento", documento)
        response = query.execute()
        for item in response.data:
            item["similarity"] = 1.0
            results.append(item)

    return results


def search(
    query: str,
    documento: str | None = None,
    k: int = 5,
) -> list[dict]:
    """Busca chunks por similitud semántica o por número de artículo.

    Si la query contiene "artículo N", busca directamente por número.
    """
    # Buscar por número de artículo
    article_numbers = _extract_article_numbers(query)
    if article_numbers:
        exact_results = _fetch_articles_by_number(article_numbers, documento)
        if exact_results:
            query_embedding = get_embeddings().embed_query(query)
            client = _get_client()

            semantic_results = []
            for doc_type in (["pregrado", "posgrado"] if not documento else [documento]):
                response = client.rpc(
                    "match_documents",
                    {
                        "query_embedding": query_embedding,
                        "match_count": k,
                        "filter_documento": doc_type,
                    },
                ).execute()
                semantic_results.extend(response.data)

            all_results = exact_results + [
                r for r in semantic_results
                if r["id"] not in {e["id"] for e in exact_results}
            ]
            return all_results[:k]

    # Búsqueda semántica normal
    query_embedding = get_embeddings().embed_query(query)
    client = _get_client()

    if documento:
        response = client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_count": k,
                "filter_documento": documento,
            },
        ).execute()
        return response.data

    # Sin filtro: usar match_documents_all (1 RPC en vez de 2)
    response = client.rpc(
        "match_documents_all",
        {
            "query_embedding": query_embedding,
            "match_count": k,
        },
    ).execute()

    return response.data


def delete_by_documento(documento: str) -> None:
    """Elimina todos los chunks de un documento específico."""
    client = _get_client()
    client.table("documents").delete().eq(
        "metadata->>documento", documento
    ).execute()
