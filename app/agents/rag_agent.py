from pathlib import Path

import yaml

from app.core.llm import get_llm
from app.core.vector_store import search

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
    return response.content.strip()


def ask(pregunta: str, k: int = 5, use_rewrite: bool = True) -> dict:
    """Consulta el RAG y retorna respuesta con fuentes.

    Args:
        pregunta: Pregunta del usuario.
        k: Número de chunks a recuperar.
        use_rewrite: Si True, reescribe la query para mejorar retrieval.
    """
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

    return {
        "respuesta": response.content,
        "fuentes": fuentes,
        "query_reescrita": search_query,
    }
