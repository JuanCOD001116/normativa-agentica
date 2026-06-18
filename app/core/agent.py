import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.models import Message


class AgentService:
    @staticmethod
    def get_agent_result(conversation_id: uuid.UUID, db: Session) -> dict[str, Any]:
        """
        Obtiene la ultima pregunta del usuario y la procesa con el orquestador.
        """
        last_user_message = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.role == "user",
            )
            .order_by(Message.created_at.desc())
            .first()
        )

        if not last_user_message:
            raise ValueError(
                "La conversacion no tiene mensajes de usuario para responder"
            )

        from app.agents.orchestrator import orchestrate

        return orchestrate(last_user_message.content)

    @staticmethod
    def get_agent_response(conversation_id: uuid.UUID, db: Session) -> str:
        """
        Compatibilidad con llamadas antiguas que esperan solo el texto de respuesta.
        """
        return AgentService.get_agent_result(conversation_id, db).get("response", "")
