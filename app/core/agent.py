import uuid
from sqlalchemy.orm import Session
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END

from app.core.models import Message


# --- DEFINICIÓN DEL GRAFO DEL AGENTE (LANGGRAPH) ---
# Este es un nodo simulado para el Agente UdeA. 
# En el futuro, aquí se integrará la lógica del LLM (ej: ChatOpenAI), prompts y herramientas (Tools).
def agent_node(state: MessagesState):
    messages = state["messages"]
    
    # Obtener el último mensaje del usuario para contextualizar la respuesta
    last_user_message = messages[-1].content if messages else ""
    
    reply_content = (
        f"Hola, he recibido tu consulta: '{last_user_message}'.\n\n"
        "Este es el Asistente de Normativa de la Universidad de Antioquia (UdeA) procesando "
        "tu mensaje a través de un flujo de trabajo de LangGraph."
    )
    
    return {"messages": [AIMessage(content=reply_content)]}


# Construir y compilar el flujo de LangGraph
workflow = StateGraph(MessagesState)
workflow.add_node("agent_node", agent_node)
workflow.add_edge(START, "agent_node")
workflow.add_edge("agent_node", END)
compiled_graph = workflow.compile()


# --- SERVICIO DEL AGENTE ---
class AgentService:

    @staticmethod
    def get_agent_response(conversation_id: uuid.UUID, db: Session) -> str:
        """
        Carga el historial de mensajes de la base de datos, lo traduce al formato
        de LangGraph, invoca al agente y retorna la respuesta generada.
        """
        # 1. Obtener el historial completo de mensajes ordenados cronológicamente
        db_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

        # 2. Traducir al formato de mensajes de LangChain/LangGraph
        langchain_messages = []
        for msg in db_messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))

        # 3. Invocar al grafo con el historial de la conversación
        state = {"messages": langchain_messages}
        result = compiled_graph.invoke(state)

        # 4. Retornar el contenido del último mensaje generado por el agente
        last_message = result["messages"][-1]
        return last_message.content
