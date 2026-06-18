from types import SimpleNamespace

from app.agents import orchestrator


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        response = self.responses.pop(0)
        return SimpleNamespace(content=response)


def test_route_query_always_uses_llm_for_reglamento_keyword(monkeypatch):
    fake_llm = FakeLLM(
        [
            '{"agents": ["web"], "reason": "Needs live source", '
            '"response_language": "Spanish"}'
        ]
    )
    monkeypatch.setattr(orchestrator, "get_llm", lambda: fake_llm)

    result = orchestrator.route_query("Que dice el reglamento y la web?")

    assert result["agents"] == [orchestrator.AGENT_WEB]
    assert result["reason"] == "Needs live source"
    assert len(fake_llm.calls) == 1


def test_route_query_parses_reglamento_estudiantes(monkeypatch):
    fake_llm = FakeLLM(
        [
            '{"agents": ["reglamento_estudiantes"], "reason": "Internal rules", '
            '"response_language": "Spanish"}'
        ]
    )
    monkeypatch.setattr(orchestrator, "get_llm", lambda: fake_llm)

    result = orchestrator.route_query("Cuales son las causales de expulsion?")

    assert result["agents"] == [orchestrator.AGENT_REGLAMENTO_ESTUDIANTES]
    assert result["response_language"] == "Spanish"


def test_route_query_parses_both_agents(monkeypatch):
    fake_llm = FakeLLM(
        [
            '{"agents": ["reglamento_estudiantes", "web"], '
            '"reason": "Needs internal and current context", '
            '"response_language": "Spanish"}'
        ]
    )
    monkeypatch.setattr(orchestrator, "get_llm", lambda: fake_llm)

    result = orchestrator.route_query("Compara el reglamento con la normativa vigente.")

    assert result["agents"] == [
        orchestrator.AGENT_REGLAMENTO_ESTUDIANTES,
        orchestrator.AGENT_WEB,
    ]


def test_route_query_falls_back_on_invalid_json(monkeypatch):
    fake_llm = FakeLLM(["not json"])
    monkeypatch.setattr(orchestrator, "get_llm", lambda: fake_llm)

    result = orchestrator.route_query("Pregunta ambigua")

    assert result["agents"] == [orchestrator.AGENT_REGLAMENTO_ESTUDIANTES]
    assert result["reason"] == orchestrator.FALLBACK_ROUTING_REASON


def test_route_query_falls_back_on_unknown_agent(monkeypatch):
    fake_llm = FakeLLM(
        ['{"agents": ["unknown"], "reason": "Bad", "response_language": "Spanish"}']
    )
    monkeypatch.setattr(orchestrator, "get_llm", lambda: fake_llm)

    result = orchestrator.route_query("Pregunta ambigua")

    assert result["agents"] == [orchestrator.AGENT_REGLAMENTO_ESTUDIANTES]


def test_agent_reglamento_estudiantes_normalizes_rag_output(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "rag_ask",
        lambda query: {
            "respuesta": "Respuesta RAG",
            "fuentes": [{"documento": "pregrado"}],
            "query_reescrita": "consulta formal",
        },
    )

    result = orchestrator.agent_reglamento_estudiantes("Pregunta")

    assert result["agent"] == orchestrator.AGENT_REGLAMENTO_ESTUDIANTES
    assert result["response"] == "Respuesta RAG"
    assert result["sources"] == [{"documento": "pregrado"}]
    assert result["query_reescrita"] == "consulta formal"


def test_orchestrate_calls_rag_for_reglamento_estudiantes(monkeypatch):
    fake_llm = FakeLLM(
        [
            '{"agents": ["reglamento_estudiantes"], "reason": "Internal rules", '
            '"response_language": "Spanish"}'
        ]
    )
    monkeypatch.setattr(orchestrator, "get_llm", lambda: fake_llm)
    monkeypatch.setattr(orchestrator, "_handle_smalltalk", lambda query: None)
    monkeypatch.setattr(
        orchestrator,
        "rag_ask",
        lambda query: {
            "respuesta": f"RAG para {query}",
            "fuentes": [],
            "query_reescrita": query,
        },
    )

    result = orchestrator.orchestrate("Pregunta de reglamento")

    assert result["agents"] == [orchestrator.AGENT_REGLAMENTO_ESTUDIANTES]
    assert result["response"] == "RAG para Pregunta de reglamento"
    assert orchestrator.AGENT_REGLAMENTO_ESTUDIANTES in result["agent_details"]


def test_orchestrate_runs_both_agents_and_synthesizes(monkeypatch):
    fake_llm = FakeLLM(
        [
            '{"agents": ["reglamento_estudiantes", "web"], '
            '"reason": "Needs both", "response_language": "Spanish"}',
            "Respuesta final sintetizada",
        ]
    )
    import app.agents.validator_agent as validator_agent

    monkeypatch.setattr(
        validator_agent, "validate", lambda q, r: {"valid": True, "reason": "Mocked"}
    )
    import app.agents.rag_agent_professors as rag_agent_professors

    monkeypatch.setattr(
        rag_agent_professors,
        "ask",
        lambda query: {
            "respuesta": "Respuesta Profesores",
            "fuentes": [],
            "query_reescrita": query,
        },
    )
    monkeypatch.setattr(orchestrator, "get_llm", lambda: fake_llm)
    monkeypatch.setattr(orchestrator, "_handle_smalltalk", lambda query: None)
    monkeypatch.setattr(
        orchestrator,
        "rag_ask",
        lambda query: {
            "respuesta": "Respuesta RAG",
            "fuentes": [{"documento": "pregrado"}],
            "query_reescrita": query,
        },
    )

    result = orchestrator.orchestrate("Compara reglamento y web")

    assert result["agents"] == [
        orchestrator.AGENT_REGLAMENTO_ESTUDIANTES,
        orchestrator.AGENT_WEB,
    ]
    assert result["response"] == "Respuesta final sintetizada"
    assert orchestrator.AGENT_REGLAMENTO_ESTUDIANTES in result["agent_details"]
    assert orchestrator.AGENT_WEB in result["agent_details"]
    assert len(fake_llm.calls) == 2
    assert (
        "same language as the original user question" in fake_llm.calls[1][0]["content"]
    )
