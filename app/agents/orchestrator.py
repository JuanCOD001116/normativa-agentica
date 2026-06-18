"""
Orquestador principal del sistema de normativa.

Responsable de enrutar consultas hacia el agente apropiado:
- Agente de documentos (AG_DOC): para consultas sobre reglamento interno
- Agente de scraping (AG_SCRAPE): para consultas de normativa web en vivo

Este módulo define interfaces claras para que otros componentes se conecten cuando estén listos.
"""

from typing import Any, Callable, Dict, Optional

# Constantes para tipos de agente
AGENT_DOCUMENTS = "doc"
AGENT_SCRAPING = "web"

# Palabras clave para detectar tipo de consulta
KEYWORDS_DOC = {
    "reglamento",
    "documento",
    "interno",
    "política",
    "procedimiento",
    "normativo",
    "manual",
    "guía",
}
KEYWORDS_WEB = {
    "web",
    "normativa",
    "vivo",
    "actual",
    "consulta",
    "en línea",
    "online",
    "corriente",
}


def detect_agent_by_keywords(query: str) -> Optional[str]:
    """
    Detecta el tipo de agente necesario basado en palabras clave.

    Args:
        query: Pregunta del usuario

    Returns:
        AGENT_DOCUMENTS ("doc") para Agente de Documentos
        AGENT_SCRAPING ("web") para Agente de Scraping
        None si es ambiguo o no hay matches claros
    """
    query_lower = query.lower()

    doc_matches = sum(1 for kw in KEYWORDS_DOC if kw in query_lower)
    web_matches = sum(1 for kw in KEYWORDS_WEB if kw in query_lower)

    if doc_matches > web_matches:
        return AGENT_DOCUMENTS
    elif web_matches > doc_matches:
        return AGENT_SCRAPING

    # Si hay igualdad o no hay matches claros, retorna None para que use LLM fallback
    return None


def detect_agent_by_llm(query: str) -> str:
    """
    Usa un LLM ligero para decidir el tipo de agente cuando keywords no es concluyente.

    Por ahora: lógica simple basada en heurística.
    TODO: Integrar LLM real aquí para mejor precision.

    Args:
        query: Pregunta del usuario

    Returns:
        AGENT_DOCUMENTS ("doc") o AGENT_SCRAPING ("web")
    """
    # Heurística: preguntas interrogativas amplias tienden a necesitar búsqueda en vivo
    interrogatives = ["cuál", "cuáles", "dónde", "cuándo", "cómo", "por qué", "quién"]
    if any(word in query.lower() for word in interrogatives):
        return AGENT_SCRAPING

    # Default a documento (consulta interna)
    return AGENT_DOCUMENTS


def route_query(query: str) -> Dict[str, Any]:
    """
    Enruta la consulta al agente apropiado usando keywords + LLM fallback.

    Args:
        query: Pregunta del usuario

    Returns:
        Dict con 'agent' (tipo de agente) y 'reason' (explicación del routing)
    """
    agent = detect_agent_by_keywords(query)
    reason = ""

    if agent is None:
        agent = detect_agent_by_llm(query)
        reason = "Routing por análisis de pregunta (keywords ambiguo)"
    else:
        if agent == AGENT_DOCUMENTS:
            reason = "Detectada palabra clave de documento interno"
        else:
            reason = "Detectada palabra clave de normativa web"

    return {"agent": agent, "reason": reason}


# ============================================================================
# MOCKS PARA AGENTES (reemplazar cuando componentes reales estén listos)
# ============================================================================


def mock_agent_documents(query: str) -> Dict[str, Any]:
    """
    Mock del Agente de Documentos.

    Retorna una respuesta quemada simulando RAG sobre reglamento interno.
    TODO: Reemplazar por implementación real cuando AG_DOC esté listo.

    Args:
        query: Pregunta del usuario

    Returns:
        Dict con structure: {'response': str, 'sources': list, 'confidence': float}
    """
    return {
        "response": f"[MOCK AG_DOC] Respuesta del Agente de Documentos para: '{query}'",
        "sources": ["reglamento_interno.pdf", "manual_procedimientos.pdf"],
        "confidence": 0.85,
        "agent": AGENT_DOCUMENTS,
    }


def mock_agent_scraping(query: str) -> Dict[str, Any]:
    """
    Mock del Agente de Scraping.

    Retorna una respuesta quemada simulando búsqueda en normativa.udea.edu.co
    TODO: Reemplazar por implementación real cuando AG_SCRAPE esté listo.

    Args:
        query: Pregunta del usuario

    Returns:
        Dict con structure: {'response': str, 'url': str, 'date_fetched': str}
    """
    return {
        "response": f"[MOCK AG_SCRAPE] Respuesta del Agente de Scraping para: '{query}'",
        "url": "https://normativa.udea.edu.co/consulta",
        "date_fetched": "2026-06-17",
        "agent": AGENT_SCRAPING,
    }


# ============================================================================
# ENTRY POINTS DEL ORQUESTADOR
# ============================================================================


def orchestrate(query: str) -> Dict[str, Any]:
    """
    Orquestador principal con mocks.

    Versión actual que usa mocks de agentes. Útil para testing y desarrollo.

    Args:
        query: Pregunta del usuario

    Returns:
        Dict con resultado completo del orquestador
    """
    print(f"\n[ORCHESTRATOR] Recibida pregunta: '{query}'")

    # 1. Routing
    routing_info = route_query(query)
    agent = routing_info["agent"]
    reason = routing_info["reason"]

    print(f"[ORCHESTRATOR] Routing: {agent} ({reason})")

    # 2. Invocar agente (mock)
    if agent == AGENT_DOCUMENTS:
        agent_response = mock_agent_documents(query)
    else:
        agent_response = mock_agent_scraping(query)

    print(f"[ORCHESTRATOR] Respuesta del agente: {agent_response['response']}")

    # 3. Retornar resultado
    result = {
        "agent": agent,
        "query": query,
        "routing_reason": reason,
        "response": agent_response["response"],
        "agent_details": agent_response,
    }

    return result


def orchestrate_with_components(
    query: str,
    agent_doc_fn: Callable[[str], Dict[str, Any]],
    agent_web_fn: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Orquestador con componentes inyectables.

    Versión para cuando los agentes reales estén listos.
    Permite inyectar funciones de agentes documentos y scraping.

    Args:
        query: Pregunta del usuario
        agent_doc_fn: Función que implementa AG_DOC. Firma: (query: str) -> Dict
        agent_web_fn: Función que implementa AG_SCRAPE. Firma: (query: str) -> Dict

    Returns:
        Dict con resultado completo del orquestador
    """
    print(f"\n[ORCHESTRATOR] Recibida pregunta: '{query}'")

    # 1. Routing
    routing_info = route_query(query)
    agent = routing_info["agent"]
    reason = routing_info["reason"]

    print(f"[ORCHESTRATOR] Routing: {agent} ({reason})")

    # 2. Invocar agente (componente real inyectado)
    if agent == AGENT_DOCUMENTS:
        agent_response = agent_doc_fn(query)
    else:
        agent_response = agent_web_fn(query)

    print(f"[ORCHESTRATOR] Respuesta del agente: {agent_response.get('response', 'N/A')}")

    # 3. Retornar resultado
    result = {
        "agent": agent,
        "query": query,
        "routing_reason": reason,
        "response": agent_response.get("response", ""),
        "agent_details": agent_response,
    }

    return result


# ============================================================================
# TESTS
# ============================================================================


if __name__ == "__main__":
    print("=" * 80)
    print("TESTS DEL ORQUESTADOR - SISTEMA DE NORMATIVA")
    print("=" * 80)

    # Casos de prueba
    test_queries = [
        "¿Cuál es el reglamento interno sobre permisos?",
        "¿Dónde puedo encontrar la normativa actual en web?",
        "¿Cómo funciona el procedimiento de solicitud de vacaciones?",
        "¿Qué normativa hay vigente?",
    ]

    print("\n--- Prueba 1: Orquestador con Mocks ---\n")
    for i, query in enumerate(test_queries, 1):
        result = orchestrate(query)
        print(f"\nResultado {i}:")
        print(f"  Agent: {result['agent']}")
        print(f"  Razón routing: {result['routing_reason']}")
        print(f"  Respuesta: {result['response']}")
        print("-" * 80)

    print("\n--- Prueba 2: Routing sin agentes ---\n")
    for query in test_queries:
        routing = route_query(query)
        print(f"Q: {query}")
        print(f"   → Agent: {routing['agent']} | Razón: {routing['reason']}\n")

    print("\n" + "=" * 80)
    print("TESTS COMPLETADOS")
    print("=" * 80)
