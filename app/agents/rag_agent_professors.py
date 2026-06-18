from pathlib import Path

import yaml

from app.core.llm import get_llm
from app.core.vector_store_professors import search_cache

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
    """Consulta el estatuto del profesor de cátedra y ocasional (tabla cache).

    Args:
        pregunta: Pregunta del usuario.
        k: Número de chunks a recuperar.
        use_rewrite: Si True, reescribe la query para mejorar retrieval.
    """
    search_query = rewrite_query(pregunta) if use_rewrite else pregunta

    chunks = search_cache(search_query, k=k)

    contexto = "\n\n".join(
        f"[Acuerdo: {c['metadata'].get('numero')} | Artículo: {c['metadata'].get('articulo')} | Capítulo: {c['metadata'].get('capitulo')}]\n{c['content']}"
        for c in chunks
    )
    fuentes = [
        {
            "codigo": c["metadata"].get("codigo"),
            "numero": c["metadata"].get("numero"),
            "fecha": c["metadata"].get("fecha"),
            "capitulo": c["metadata"].get("capitulo"),
            "articulo": c["metadata"].get("articulo"),
            "similitud": round(c["similarity"], 3),
        }
        for c in chunks
    ]

    system_prompt = _load_prompt("rag_agent_professors")
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
