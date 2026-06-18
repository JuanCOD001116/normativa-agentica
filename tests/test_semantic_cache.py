from types import SimpleNamespace
import pytest
from app.agents import rag_agent


class FakeLLM:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return SimpleNamespace(content=self.content)


class FakeEmbeddings:
    def embed_query(self, text):
        return [0.1] * 1024


def test_ask_cache_miss(monkeypatch):
    # Configurar mocks
    mock_embeddings = FakeEmbeddings()
    fake_llm = FakeLLM("Respuesta del LLM")

    cache_store = {}

    def mock_check_cache(embedding, threshold):
        return None

    def mock_add_cache(query, embedding, response_data):
        cache_store[query] = response_data

    monkeypatch.setattr(rag_agent, "get_embeddings", lambda: mock_embeddings)
    monkeypatch.setattr(rag_agent, "check_semantic_cache", mock_check_cache)
    monkeypatch.setattr(rag_agent, "add_to_semantic_cache", mock_add_cache)
    monkeypatch.setattr(rag_agent, "rewrite_query", lambda q: "consulta formal")
    monkeypatch.setattr(
        rag_agent,
        "search",
        lambda q, k: [
            {
                "content": "contenido del chunk",
                "metadata": {"documento": "pregrado", "articulo": "1"},
                "similarity": 0.95,
            }
        ],
    )
    monkeypatch.setattr(rag_agent, "get_llm", lambda: fake_llm)

    # Ejecución del RAG con Miss de caché
    res = rag_agent.ask("¿cuál es la sanción por copia?", k=1, use_rewrite=True)

    assert res["respuesta"] == "Respuesta del LLM"
    assert res["cached"] is False
    assert len(fake_llm.calls) == 1
    assert "¿cuál es la sanción por copia?" in cache_store


def test_ask_cache_hit(monkeypatch):
    # Configurar mocks
    mock_embeddings = FakeEmbeddings()

    cached_response = {
        "respuesta": "Respuesta Cacheada",
        "fuentes": [{"documento": "pregrado", "articulo": "1", "similitud": 0.95}],
        "query_reescrita": "consulta formal",
        "cached": False,
    }

    def mock_check_cache(embedding, threshold):
        return {
            "query": "¿cuál es la sanción por copia?",
            "response": cached_response.copy(),
            "similarity": 0.98,
        }

    def mock_add_cache(query, embedding, response_data):
        pytest.fail("No se debería intentar añadir a caché en un hit")

    monkeypatch.setattr(rag_agent, "get_embeddings", lambda: mock_embeddings)
    monkeypatch.setattr(rag_agent, "check_semantic_cache", mock_check_cache)
    monkeypatch.setattr(rag_agent, "add_to_semantic_cache", mock_add_cache)

    # Ejecución del RAG con Hit de caché
    res = rag_agent.ask("¿cuál es la sanción por copia?", k=1, use_rewrite=True)

    assert res["respuesta"] == "Respuesta Cacheada"
    assert res["cached"] is True
    assert res["similitud_cache"] == 0.98
