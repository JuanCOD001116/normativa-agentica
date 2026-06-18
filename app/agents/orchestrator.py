"""Orquestador principal del sistema de normativa."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import yaml

AGENT_REGLAMENTO_ESTUDIANTES = "reglamento_estudiantes"
AGENT_PROFESORES = "profesores"

# Aliases de compatibilidad para imports existentes.
AGENT_DOCUMENTS = AGENT_REGLAMENTO_ESTUDIANTES
AGENT_WEB = AGENT_PROFESORES
AGENT_SCRAPING = AGENT_PROFESORES

VALID_AGENTS = {AGENT_REGLAMENTO_ESTUDIANTES, AGENT_PROFESORES}
FALLBACK_ROUTING_REASON = (
    "Fallback to student regulations agent after invalid orchestrator LLM output"
)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def get_llm() -> Any:
    from app.core.llm import get_llm as core_get_llm

    return core_get_llm()


def _handle_smalltalk(query: str) -> dict[str, Any] | None:
    """Detecta saludos y mensajes conversacionales y responde directamente.

    Retorna un resultado listo si es small talk, None si es una pregunta de normativa.
    """
    llm = get_llm()
    messages = [
        {
            "role": "system",
            "content": (
                "Classify the following message as either 'smalltalk' or 'normativa'.\n"
                "'smalltalk': ONLY pure greetings (hola, hi, buenos días), farewells (adiós, chao), "
                "or single-word thanks (gracias). Nothing else.\n"
                "'normativa': everything else — questions, requests, opinions, topics about the university, "
                "regulations, or anything that requires a substantive answer.\n"
                "When in doubt, classify as normativa.\n"
                "Reply with only one word: smalltalk or normativa."
            ),
        },
        {"role": "user", "content": query},
    ]
    try:
        result = llm.invoke(messages)
        classification = getattr(result, "content", "").strip().lower()
    except Exception:
        classification = "normativa"

    if "smalltalk" not in classification:
        return None

    greeting_messages = [
        {
            "role": "system",
            "content": (
                "You are a university regulation assistant for Universidad de Antioquia. "
                "The user just sent a greeting or farewell. Respond briefly and warmly. "
                "Do NOT answer any questions or give opinions. "
                "Just greet back and mention you are here to help with university regulations. "
                "Respond in the same language as the user. Maximum 2 sentences."
            ),
        },
        {"role": "user", "content": query},
    ]
    try:
        greeting_result = llm.invoke(greeting_messages)
        response = getattr(greeting_result, "content", "¡Hola! ¿En qué te puedo ayudar con la normativa universitaria?").strip()
    except Exception:
        response = "¡Hola! ¿En qué te puedo ayudar con la normativa universitaria?"

    return {
        "agents": ["smalltalk"],
        "query": query,
        "routing_reason": "Conversational message detected",
        "response_language": "same language as the user input",
        "response": response,
        "agent_details": {},
        "validation": {"valid": True, "reason": "Smalltalk — no normativa validation needed"},
        "attempts": 1,
    }


def rag_ask(query: str) -> dict[str, Any]:
    from app.agents.rag_agent import ask

    return ask(query)


def _load_prompt(name: str, key: str = "system_prompt") -> str:
    with open(_PROMPTS_DIR / f"{name}.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data[key]


def _message_content(response: Any) -> str:
    return getattr(response, "content", str(response)).strip()


def _fallback_route() -> dict[str, Any]:
    return {
        "agents": [AGENT_REGLAMENTO_ESTUDIANTES],
        "reason": FALLBACK_ROUTING_REASON,
        "response_language": "same language as the user input",
    }


def _parse_route_response(content: str) -> dict[str, Any]:
    data = json.loads(content)
    agents = data.get("agents")

    if not isinstance(agents, list) or not agents:
        raise ValueError("Expected non-empty agents list")

    normalized_agents: list[str] = []
    for agent in agents:
        if agent not in VALID_AGENTS:
            raise ValueError(f"Unknown agent: {agent}")
        if agent not in normalized_agents:
            normalized_agents.append(agent)

    reason = data.get("reason")
    response_language = data.get("response_language")

    return {
        "agents": normalized_agents,
        "reason": reason if isinstance(reason, str) and reason else "LLM routing",
        "response_language": (
            response_language
            if isinstance(response_language, str) and response_language
            else "same language as the user input"
        ),
    }


def route_query(query: str) -> dict[str, Any]:
    """Enruta la consulta usando siempre el LLM del orquestador."""
    try:
        llm = get_llm()
        messages = [
            {"role": "system", "content": _load_prompt("orchestrator")},
            {"role": "user", "content": query},
        ]
        response = llm.invoke(messages)
        return _parse_route_response(_message_content(response))
    except Exception:
        return _fallback_route()


def agent_reglamento_estudiantes(query: str) -> dict[str, Any]:
    """Tool del agente RAG de reglamento estudiantes."""
    rag_result = rag_ask(query)
    return {
        "response": rag_result.get("respuesta", ""),
        "sources": rag_result.get("fuentes", []),
        "query_reescrita": rag_result.get("query_reescrita"),
        "agent": AGENT_REGLAMENTO_ESTUDIANTES,
        "raw": rag_result,
    }


def agent_profesores(query: str) -> dict[str, Any]:
    """Agente especializado en el Estatuto del Profesor de Cátedra y Ocasional."""
    from app.agents.rag_agent_professors import ask

    rag_result = ask(query)
    return {
        "response": rag_result.get("respuesta", ""),
        "sources": rag_result.get("fuentes", []),
        "query_reescrita": rag_result.get("query_reescrita"),
        "agent": AGENT_PROFESORES,
        "raw": rag_result,
    }


def _synthesize_response(
    query: str,
    routing_info: dict[str, Any],
    agent_details: dict[str, dict[str, Any]],
) -> str:
    llm = get_llm()
    agent_outputs = json.dumps(agent_details, ensure_ascii=False, indent=2)
    messages = [
        {"role": "system", "content": _load_prompt("orchestrator", "synthesis_prompt")},
        {
            "role": "user",
            "content": (
                f"Original user question:\n{query}\n\n"
                f"Routing decision:\n{json.dumps(routing_info, ensure_ascii=False)}\n\n"
                f"Agent outputs:\n{agent_outputs}"
            ),
        },
    ]
    response = llm.invoke(messages)
    return _message_content(response)


def _fallback_combined_response(agent_details: dict[str, dict[str, Any]]) -> str:
    return "\n\n".join(
        detail.get("response", "")
        for detail in agent_details.values()
        if detail.get("response")
    )


def _run_selected_agents(
    query: str,
    agents: list[str],
    agent_reglamento_fn: Callable[[str], dict[str, Any]],
    agent_web_fn: Callable[[str], dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    agent_details: dict[str, dict[str, Any]] = {}

    for agent in agents:
        if agent == AGENT_REGLAMENTO_ESTUDIANTES:
            agent_details[agent] = agent_reglamento_fn(query)
        elif agent == AGENT_WEB:
            agent_details[agent] = agent_web_fn(query)

    return agent_details


def _build_orchestration_result(
    query: str,
    routing_info: dict[str, Any],
    agent_details: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if len(agent_details) == 1:
        response = next(iter(agent_details.values())).get("response", "")
    else:
        try:
            response = _synthesize_response(query, routing_info, agent_details)
        except Exception:
            response = _fallback_combined_response(agent_details)

    return {
        "agents": routing_info["agents"],
        "query": query,
        "routing_reason": routing_info["reason"],
        "response_language": routing_info["response_language"],
        "response": response,
        "agent_details": agent_details,
    }


_MAX_VALIDATION_RETRIES = 2
_FALLBACK_RESPONSE = (
    "Lo siento, no encontré información suficiente en la normativa disponible para responder "
    "tu pregunta. Te recomendamos consultar directamente con la Secretaría General de la "
    "Universidad de Antioquia o visitar normativa.udea.edu.co."
)


def orchestrate(query: str) -> dict[str, Any]:
    """Orquesta la consulta con validación al final del flujo (máx. 2 reintentos)."""
    from app.agents.validator_agent import validate

    smalltalk = _handle_smalltalk(query)
    if smalltalk is not None:
        return smalltalk

    last_result: dict[str, Any] = {}

    for attempt in range(1, _MAX_VALIDATION_RETRIES + 1):
        routing_info = route_query(query)
        agent_details = _run_selected_agents(
            query=query,
            agents=routing_info["agents"],
            agent_reglamento_fn=agent_reglamento_estudiantes,
            agent_web_fn=agent_profesores,
        )
        result = _build_orchestration_result(query, routing_info, agent_details)

        validation = validate(query, result["response"])
        result["validation"] = validation
        result["attempts"] = attempt
        last_result = result

        if validation["valid"]:
            return result

    last_result["response"] = _FALLBACK_RESPONSE
    return last_result


def orchestrate_with_components(
    query: str,
    agent_doc_fn: Callable[[str], dict[str, Any]],
    agent_web_fn: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    """Orquesta con componentes inyectables para pruebas o integraciones."""
    routing_info = route_query(query)
    agent_details = _run_selected_agents(
        query=query,
        agents=routing_info["agents"],
        agent_reglamento_fn=agent_doc_fn,
        agent_web_fn=agent_web_fn,
    )
    return _build_orchestration_result(query, routing_info, agent_details)


if __name__ == "__main__":
    test_queries = [
        "Cual es el reglamento sobre permanencia estudiantil?",
        "Consulta normativa vigente en la web y comparala con el reglamento.",
    ]

    for test_query in test_queries:
        result = orchestrate(test_query)
        print(json.dumps(result, ensure_ascii=False, indent=2))
