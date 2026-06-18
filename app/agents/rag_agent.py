from pathlib import Path

import yaml

from app.core.embeddings import get_embeddings
from app.core.llm import get_llm
from app.core.vector_store import (
    search,
    check_semantic_cache,
    add_to_semantic_cache,
)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _load_prompt(name: str) -> str:
    with open(_PROMPTS_DIR / f"{name}.yaml") as f:
        data = yaml.safe_load(f)
    return data["system_prompt"]


def rewrite_query(pregunta: str) -> str:
    """Reescribe la pregunta del usuario para mejorar el retrieval."""
    llm = get_llm()
    prompt = _load_prompt("query_rewriter")

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": pregunta},
    ]

    response = llm.invoke(messages)
    return str(response.content).strip()


def ask(
    pregunta: str, k: int = 5, use_rewrite: bool = True, cache_threshold: float = 0.92
) -> dict:
    """Consulta el RAG y retorna respuesta con fuentes.

    Args:
        pregunta: Pregunta del usuario.
        k: Número de chunks a recuperar.
        use_rewrite: Si True, reescribe la query para mejorar retrieval.
        cache_threshold: Umbral de similitud semántica para usar la caché.
    """
    # Intentar obtener respuesta de la caché semántica
    query_embedding = None
    try:
        query_embedding = get_embeddings().embed_query(pregunta)
        cached_result = check_semantic_cache(query_embedding, threshold=cache_threshold)
        if cached_result:
            # cached_result["response"] contiene el dict con la respuesta y fuentes
            response_data = cached_result["response"]
            # Marcamos que proviene de la caché
            response_data["cached"] = True
            response_data["similitud_cache"] = round(
                cached_result.get("similarity", 0.0), 3
            )
            return response_data
    except Exception as e:
        # En caso de error de red o base de datos en la caché, continuar con el flujo normal
        print(f"Error al verificar la caché semántica: {e}")

    # Paso 1: Query rewriting
    search_query = rewrite_query(pregunta) if use_rewrite else pregunta

    # Paso 2: Búsqueda
    chunks = search(search_query, k=k)

    # Paso 3: Construir contexto
    contexto = "\n\n".join(
        f"[Documento: {c['metadata'].get('documento')} | Artículo: {c['metadata'].get('articulo')}]\n{c['content']}"
        for c in chunks
    )
    fuentes = [
        {
            "documento": c["metadata"].get("documento"),
            "capitulo": c["metadata"].get("capitulo"),
            "articulo": c["metadata"].get("articulo"),
            "similitud": round(c["similarity"], 3),
        }
        for c in chunks
    ]

    # Paso 4: Generar respuesta con pregunta original
    system_prompt = _load_prompt("rag_agent")
    llm = get_llm()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{contexto}\n\nQuestion: {pregunta}"},
    ]

    response = llm.invoke(messages)

    resultado = {
        "respuesta": response.content,
        "fuentes": fuentes,
        "query_reescrita": search_query,
        "cached": False,
    }

    # Guardar en la caché semántica si pudimos generar el embedding de la pregunta original
    if query_embedding is None:
        try:
            query_embedding = get_embeddings().embed_query(pregunta)
        except Exception as e:
            print(f"Error al calcular embedding para guardar en caché: {e}")
            query_embedding = None

    if query_embedding is not None:
        add_to_semantic_cache(pregunta, query_embedding, resultado)

    return resultado
