import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- ESQUEMAS DE MENSAJES ---
class MessageBase(BaseModel):
    role: str = Field(..., description="Rol del emisor: user, assistant, system, tool")
    content: str = Field(..., description="Contenido textual del mensaje")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales del mensaje")


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- ESQUEMAS DE CONVERSACIONES ---
class ConversationBase(BaseModel):
    title: Optional[str] = Field("Nueva conversación", description="Título descriptivo del chat")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Configuraciones o datos adicionales del chat")


class ConversationCreate(ConversationBase):
    user_id: str = Field(..., description="ID del usuario obtenido de localStorage")


class ConversationResponse(ConversationBase):
    id: uuid.UUID
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Nuevo título de la conversación")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Nuevos metadatos de la conversación")
