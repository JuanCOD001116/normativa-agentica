import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.api.main import app
from app.core.database import Base, get_db

# Configuración de base de datos de prueba en memoria
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Sobrescribir la dependencia get_db
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def run_around_tests():
    # Crear tablas antes de cada test
    Base.metadata.create_all(bind=engine)
    yield
    # Limpiar tablas después de cada test
    Base.metadata.drop_all(bind=engine)


def test_create_and_list_conversations():
    # 1. Crear conversación
    response = client.post(
        "/api/conversations/",
        json={
            "user_id": "test_user_123",
            "title": "Test Chat",
            "meta_data": {"origin": "web"},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == "test_user_123"
    assert data["title"] == "Test Chat"
    assert "id" in data

    conversation_id = data["id"]

    # 2. Listar conversaciones de ese usuario
    response = client.get("/api/conversations/?user_id=test_user_123")
    assert response.status_code == 200
    conversations = response.json()
    assert len(conversations) == 1
    assert conversations[0]["id"] == conversation_id

    # 3. Listar conversaciones de otro usuario (debe estar vacía)
    response = client.get("/api/conversations/?user_id=other_user")
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_add_and_get_messages():
    # 1. Crear conversación
    response = client.post(
        "/api/conversations/",
        json={"user_id": "test_user_123", "title": "Test Chat"},
    )
    conversation_id = response.json()["id"]

    # 2. Añadir un mensaje del usuario
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"role": "user", "content": "Hola, ¿quién eres?"},
    )
    assert response.status_code == 201
    msg_data = response.json()
    assert msg_data["role"] == "user"
    assert msg_data["content"] == "Hola, ¿quién eres?"
    assert msg_data["conversation_id"] == conversation_id

    # 3. Añadir respuesta del asistente
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "role": "assistant",
            "content": "Hola, soy tu asistente de normativa.",
            "meta_data": {"tokens": 10},
        },
    )
    assert response.status_code == 201

    # 4. Obtener detalle de conversación (debe incluir mensajes)
    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["meta_data"]["tokens"] == 10


def test_delete_conversation():
    # 1. Crear conversación
    response = client.post(
        "/api/conversations/",
        json={"user_id": "test_user_123", "title": "Test Chat"},
    )
    conversation_id = response.json()["id"]

    # 2. Eliminar conversación
    response = client.delete(f"/api/conversations/{conversation_id}")
    assert response.status_code == 204

    # 3. Comprobar que ya no existe
    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 404


def test_ask_agent_uses_orchestrator_result_and_stores_assistant_message(monkeypatch):
    response = client.post(
        "/api/conversations/",
        json={"user_id": "test_user_123", "title": "Test Chat"},
    )
    conversation_id = response.json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"role": "user", "content": "Que dice el reglamento?"},
    )
    assert response.status_code == 201

    def fake_agent_result(conversation_id, db):
        return {
            "agents": ["reglamento_estudiantes"],
            "routing_reason": "Test routing",
            "response_language": "Spanish",
            "response": "Respuesta desde el orquestador",
            "agent_details": {
                "reglamento_estudiantes": {
                    "response": "Respuesta desde el orquestador",
                    "sources": [],
                }
            },
        }

    monkeypatch.setattr(
        "app.api.routes.conversations.AgentService.get_agent_result",
        fake_agent_result,
    )

    response = client.post(f"/api/conversations/{conversation_id}/ask")

    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "assistant"
    assert data["content"] == "Respuesta desde el orquestador"
    assert data["meta_data"]["agents"] == ["reglamento_estudiantes"]
    assert data["meta_data"]["routing_reason"] == "Test routing"

    response = client.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
