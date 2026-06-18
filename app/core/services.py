import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.models import Conversation, Message


class ConversationService:
    @staticmethod
    def create_conversation(
        db: Session,
        user_id: str,
        title: Optional[str] = "Nueva conversación",
        meta_data: Optional[dict] = None,
    ) -> Conversation:
        """
        Crea una nueva conversación para un usuario.
        """
        db_conversation = Conversation(
            user_id=user_id, title=title, meta_data=meta_data
        )
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation

    @staticmethod
    def get_conversations_by_user(db: Session, user_id: str) -> List[Conversation]:
        """
        Obtiene todas las conversaciones de un usuario ordenadas por la más reciente.
        """
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    @staticmethod
    def get_conversation(
        db: Session, conversation_id: uuid.UUID
    ) -> Optional[Conversation]:
        """
        Obtiene el detalle de una conversación específica.
        """
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    @staticmethod
    def add_message(
        db: Session,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        meta_data: Optional[dict] = None,
    ) -> Optional[Message]:
        """
        Agrega un nuevo mensaje a una conversación existente y actualiza su fecha de modificación.
        """
        db_conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )
        if not db_conversation:
            return None

        db_message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            meta_data=meta_data,
        )
        db.add(db_message)

        # Actualizar timestamp de modificación del chat
        db_conversation.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_message)
        return db_message

    @staticmethod
    def delete_conversation(db: Session, conversation_id: uuid.UUID) -> bool:
        """
        Elimina una conversación y todos sus mensajes asociados en cascada.
        """
        db_conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )
        if not db_conversation:
            return False
        db.delete(db_conversation)
        db.commit()
        return True

    @staticmethod
    def update_conversation(
        db: Session,
        conversation_id: uuid.UUID,
        title: Optional[str] = None,
        meta_data: Optional[dict] = None,
    ) -> Optional[Conversation]:
        """
        Actualiza el título y/o metadatos de una conversación.
        """
        db_conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )
        if not db_conversation:
            return None
        if title is not None:
            db_conversation.title = title
        if meta_data is not None:
            db_conversation.meta_data = meta_data
        db.commit()
        db.refresh(db_conversation)
        return db_conversation
