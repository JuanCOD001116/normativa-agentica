import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.schemas import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.core.services import ConversationService
from app.core.agent import AgentService

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post(
    "/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED
)
def create_conversation(
    conversation: ConversationCreate, db: Session = Depends(get_db)
):
    """
    Crea una nueva sesión de conversación para un usuario identificado por `user_id`.
    """
    return ConversationService.create_conversation(
        db=db,
        user_id=conversation.user_id,
        title=conversation.title,
        meta_data=conversation.meta_data,
    )


@router.get("/", response_model=List[ConversationResponse])
def list_conversations(
    user_id: str = Query(..., description="ID del usuario obtenido de localStorage"),
    db: Session = Depends(get_db),
):
    """
    Obtiene el listado de conversaciones asociadas a un `user_id`.
    """
    return ConversationService.get_conversations_by_user(db=db, user_id=user_id)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Obtiene los detalles de una conversación específica, incluyendo su historial de mensajes.
    """
    db_conversation = ConversationService.get_conversation(
        db=db, conversation_id=conversation_id
    )
    if not db_conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada",
        )
    return db_conversation


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    conversation_id: uuid.UUID,
    message: MessageCreate,
    db: Session = Depends(get_db),
):
    """
    Agrega un nuevo mensaje a una conversación activa.
    """
    db_message = ConversationService.add_message(
        db=db,
        conversation_id=conversation_id,
        role=message.role,
        content=message.content,
        meta_data=message.meta_data,
    )
    if not db_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada",
        )
    return db_message


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Elimina una conversación y sus mensajes en cascada.
    """
    success = ConversationService.delete_conversation(
        db=db, conversation_id=conversation_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada",
        )
    return


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: uuid.UUID,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db),
):
    """
    Actualiza el título o los metadatos de una conversación.
    """
    db_conversation = ConversationService.update_conversation(
        db=db,
        conversation_id=conversation_id,
        title=conversation_update.title,
        meta_data=conversation_update.meta_data,
    )
    if not db_conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada",
        )
    return db_conversation


@router.post(
    "/{conversation_id}/ask",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def ask_agent(conversation_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Invoca al orquestador para responder la ultima consulta del usuario,
    guardando su respuesta en la base de datos de forma persistente.
    """
    try:
        agent_result = AgentService.get_agent_result(conversation_id, db)

        db_message = ConversationService.add_message(
            db=db,
            conversation_id=conversation_id,
            role="assistant",
            content=agent_result.get("response", ""),
            meta_data={
                "agents": agent_result.get("agents", []),
                "routing_reason": agent_result.get("routing_reason"),
                "response_language": agent_result.get("response_language"),
                "agent_details": agent_result.get("agent_details", {}),
            },
        )
        if not db_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada",
            )
        return db_message
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la respuesta del agente: {str(e)}",
        )
