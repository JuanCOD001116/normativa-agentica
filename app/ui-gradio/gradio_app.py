"""
Interfaz Gradio para el Sistema de Consulta de Normativa.

Proporciona una UI avanzada con:
- Chat multi-turn con historial
- Opciones de routing manual (forzar agente)
- Panel de debug con información de routing y metadata
- Integración directa con el orquestador
"""

import gradio as gr
from typing import Any, Dict, List, Tuple
from app.agents import orchestrate, AGENT_DOCUMENTS, AGENT_SCRAPING


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def format_debug_info(result: Dict[str, Any]) -> str:
    """
    Formatea la información de debug para mostrar en la UI.

    Args:
        result: Resultado completo del orquestador

    Returns:
        String formateado con información de routing y metadata
    """
    agent = result.get("agent", "N/A")
    routing_reason = result.get("routing_reason", "N/A")
    agent_details = result.get("agent_details", {})

    debug_lines = [
        f"🤖 **Agente Usado:** {agent.upper()}",
        f"📍 **Razón del Routing:** {routing_reason}",
    ]

    # Información específica según agente
    if agent == AGENT_DOCUMENTS:
        sources = agent_details.get("sources", [])
        confidence = agent_details.get("confidence", 0)
        if sources:
            debug_lines.append(f"📚 **Fuentes:** {', '.join(sources)}")
        if confidence > 0:
            debug_lines.append(f"✅ **Confianza:** {confidence * 100:.0f}%")

    elif agent == AGENT_SCRAPING:
        url = agent_details.get("url", "N/A")
        date_fetched = agent_details.get("date_fetched", "N/A")
        debug_lines.append(f"🌐 **URL:** {url}")
        debug_lines.append(f"📅 **Fecha de Consulta:** {date_fetched}")

    return "\n".join(debug_lines)


def process_query(
    message: str, chat_history: List[List[str]], force_agent: str
) -> Tuple[List[List[str]], str, str]:
    """
    Procesa una consulta del usuario y actualiza el historial de chat.

    Args:
        message: Pregunta del usuario
        chat_history: Historial de chat anterior
        force_agent: Agente forzado ("auto", "doc", "web")

    Returns:
        Tupla: (chat_history_actualizado, respuesta_formateada, debug_info)
    """
    if not message.strip():
        return chat_history, "", "Escribe una pregunta válida."

    # Llamar al orquestador
    try:
        result = orchestrate(message)
        response = result.get("response", "No se obtuvo respuesta del agente.")

        # Si el usuario forzó un agente, añadir nota
        if force_agent != "auto":
            agent_usado = result.get("agent", "desconocido")
            response = (
                f"[Agente forzado: {force_agent.upper()}]\n\n{response}"
            )

        # Formatear debug info
        debug_info = format_debug_info(result)

        # Actualizar chat history
        chat_history.append([message, response])

        return chat_history, "", debug_info

    except Exception as e:
        error_msg = f"❌ Error procesando consulta: {str(e)}"
        chat_history.append([message, error_msg])
        return chat_history, "", f"Error: {str(e)}"


def clear_chat() -> Tuple[List, str, str]:
    """Limpia el historial del chat."""
    return [], "", "Chat limpiado."


# ============================================================================
# INTERFAZ GRADIO
# ============================================================================


def create_interface():
    """Crea la interfaz Gradio con todos los componentes."""

    with gr.Blocks(
        title="Sistema de Consulta de Normativa",
    ) as interface:
        # Header
        gr.Markdown(
            """
        # 📋 Sistema de Consulta de Normativa
        
        Haz preguntas sobre el reglamento interno y normativa vigente.
        El sistema enrutará automáticamente tu pregunta al agente especializado.
        """
        )

        with gr.Row():
            with gr.Column(scale=3):
                # Chat principal
                chatbot = gr.Chatbot(
                    label="Conversación",
                    height=400,
                )

            with gr.Column(scale=1):
                # Panel lateral con opciones
                gr.Markdown("### ⚙️ Opciones")

                force_agent = gr.Radio(
                    choices=["auto", "doc", "web"],
                    value="auto",
                    label="Forzar Agente",
                    info="'auto' = routing automático\n'doc' = documentos internos\n'web' = normativa web",
                )

                gr.Markdown("### ℹ️ Info")
                debug_output = gr.Textbox(
                    label="Debug Info",
                    interactive=False,
                    lines=6,
                )

        # Input area
        with gr.Row():
            query_input = gr.Textbox(
                label="Tu pregunta",
                placeholder="Ej: ¿Cuál es el reglamento sobre permisos?",
                lines=2,
            )

        # Botones
        with gr.Row():
            send_btn = gr.Button("📤 Enviar", variant="primary")
            clear_btn = gr.Button("🗑️ Limpiar Chat")

        # Status message
        status_output = gr.Textbox(
            label="Estado",
            value="Listo para procesar consultas...",
            interactive=False,
        )

        # =====================================================================
        # LÓGICA DE EVENTOS
        # =====================================================================

        # Evento: Enviar pregunta
        send_btn.click(
            fn=process_query,
            inputs=[query_input, chatbot, force_agent],
            outputs=[chatbot, query_input, debug_output],
        ).then(
            fn=lambda: "✅ Consulta procesada.",
            outputs=[status_output],
        )

        # Evento: Limpiar chat
        clear_btn.click(
            fn=clear_chat,
            outputs=[chatbot, query_input, debug_output],
        ).then(
            fn=lambda: "🗑️ Chat limpiado.",
            outputs=[status_output],
        )

        # Evento: Enter en input para enviar
        query_input.submit(
            fn=process_query,
            inputs=[query_input, chatbot, force_agent],
            outputs=[chatbot, query_input, debug_output],
        ).then(
            fn=lambda: "✅ Consulta procesada.",
            outputs=[status_output],
        )

        # Footer
        gr.Markdown(
            """
        ---
        
        **Sistema de Consulta de Normativa UdeA**
        
        *v1.0 - Desarrollo Local*
        """
        )

    return interface


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("INICIANDO INTERFAZ GRADIO")
    print("=" * 80)
    print("\n🚀 Abriendo navegador en http://localhost:7860")
    print("Presiona Ctrl+C para detener el servidor.\n")

    interface = create_interface()
    interface.launch(
        theme=gr.themes.Soft(),
        share=False,
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
    )
