import { useState, useEffect, useRef, useCallback } from "react";
import { MessageSquare, Plus, Trash2, Send, User, GraduationCap } from "lucide-react";
import { api, getOrCreateUserId } from "./api";
import logoUdea from "./assets/logo_udea.png";

function App() {
  const [userId] = useState(getOrCreateUserId);
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState(null);

  const [editingConversationId, setEditingConversationId] = useState(null);
  const [editTitleValue, setEditTitleValue] = useState("");

  const messagesEndRef = useRef(null);

  // Cargar lista de conversaciones del usuario (usado en controladores de eventos)
  const loadConversations = useCallback(async () => {
    try {
      const data = await api.getConversations(userId);
      setConversations(data);
    } catch (err) {
      console.error("Error al cargar las conversaciones:", err);
    }
  }, [userId]);

  // Cargar conversaciones al montar la app
  useEffect(() => {
    let active = true;
    const fetchConversations = async () => {
      try {
        const data = await api.getConversations(userId);
        if (active) {
          setConversations(data);
        }
      } catch (err) {
        console.error("Error al cargar las conversaciones:", err);
      }
    };
    fetchConversations();
    return () => {
      active = false;
    };
  }, [userId]);

  // Seleccionar una conversación y cargar sus mensajes
  const handleSelectConversation = async (chat) => {
    setActiveConversation(chat);
    try {
      setLoading(true);
      const detail = await api.getConversationDetail(chat.id);
      setMessages(detail.messages || []);
    } catch (err) {
      console.error("Error al cargar los mensajes:", err);
    } finally {
      setLoading(false);
    }
  };

  // Desplazar automáticamente el chat hacia abajo con cada mensaje nuevo o al escribir
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Iniciar una nueva conversación
  const handleNewConversation = async () => {
    try {
      const defaultTitle = `Consulta UdeA ${conversations.length + 1}`;
      const newChat = await api.createConversation(userId, defaultTitle);
      setConversations((prev) => [newChat, ...prev]);
      setActiveConversation(newChat);
      setMessages([]);
    } catch (err) {
      console.error("Error al crear conversación:", err);
    }
  };

  // Abrir modal de confirmación de eliminación
  const handleDeleteConversation = (e, id) => {
    e.stopPropagation();
    setConversationToDelete(id);
    setShowDeleteModal(true);
  };

  // Confirmar y realizar la eliminación de la conversación en la base de datos
  const confirmDeleteConversation = async () => {
    if (!conversationToDelete) return;
    try {
      await api.deleteConversation(conversationToDelete);
      if (activeConversation?.id === conversationToDelete) {
        setActiveConversation(null);
        setMessages([]);
      }
      loadConversations();
    } finally {
      setShowDeleteModal(false);
      setConversationToDelete(null);
    }
  };

  // Comenzar edición de título
  const handleStartEdit = (id, currentTitle) => {
    setEditingConversationId(id);
    setEditTitleValue(currentTitle);
  };

  // Guardar el título editado
  const handleSaveTitle = async (id) => {
    if (!editTitleValue.trim()) {
      setEditingConversationId(null);
      return;
    }
    try {
      const updatedChat = await api.updateConversation(id, editTitleValue.trim());
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: editTitleValue.trim() } : c))
      );
      if (activeConversation?.id === id) {
        setActiveConversation(updatedChat);
      }
    } catch (err) {
      console.error("Error al actualizar el título:", err);
    } finally {
      setEditingConversationId(null);
    }
  };

  // Enviar mensaje y simular respuesta del bot
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || !activeConversation) return;

    const userText = inputValue;
    setInputValue("");
    setIsTyping(true);

    try {
      // 1. Guardar mensaje del usuario en la base de datos
      const userMsg = await api.sendMessage(activeConversation.id, "user", userText);
      
      // Si es el primer mensaje de la conversación, actualizar el título dinámicamente
      if (messages.length === 0) {
        const truncatedTitle = userText.length > 26 ? userText.substring(0, 26) + "..." : userText;
        try {
          const updatedChat = await api.updateConversation(activeConversation.id, truncatedTitle);
          setActiveConversation(updatedChat);
          setConversations((prev) =>
            prev.map((c) => (c.id === activeConversation.id ? { ...c, title: truncatedTitle } : c))
          );
        } catch (titleErr) {
          console.error("Error al actualizar el título del chat:", titleErr);
        }
      }

      setMessages((prev) => [...prev, userMsg]);

      // 2. Llamar al backend para invocar el agente de LangGraph
      try {
        const botMsg = await api.askAgent(activeConversation.id);
        setMessages((prev) => [...prev, botMsg]);
        loadConversations(); // Recargar para actualizar fecha de modificación
      } catch (err) {
        console.error("Error al obtener respuesta del agente:", err);
      } finally {
        setIsTyping(false);
      }
    } catch (err) {
      console.error("Error al enviar mensaje:", err);
      setIsTyping(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar / Panel Lateral */}
      <div className="sidebar">
        <div className="sidebar-header">
          <img src={logoUdea} alt="UdeA Logo" className="logo-img" />
        </div>

        <div className="conversations-list">
          {conversations.map((chat) => (
            <div
              key={chat.id}
              className={`conversation-item ${activeConversation?.id === chat.id ? "active" : ""}`}
              onClick={() => {
                if (editingConversationId !== chat.id) {
                  handleSelectConversation(chat);
                }
              }}
              onDoubleClick={() => handleStartEdit(chat.id, chat.title)}
            >
              <div className="conversation-info">
                <MessageSquare size={16} />
                {editingConversationId === chat.id ? (
                  <input
                    type="text"
                    className="edit-title-input"
                    value={editTitleValue}
                    onChange={(e) => setEditTitleValue(e.target.value)}
                    onBlur={() => handleSaveTitle(chat.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        handleSaveTitle(chat.id);
                      } else if (e.key === "Escape") {
                        setEditingConversationId(null);
                      }
                    }}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <span className="conversation-title">{chat.title}</span>
                )}
              </div>
              <button
                className="delete-chat-btn"
                onClick={(e) => handleDeleteConversation(e, chat.id)}
                title="Eliminar chat"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <button className="new-chat-btn" onClick={handleNewConversation}>
            <Plus size={18} />
            Nuevo Chat
          </button>
        </div>
      </div>

      {/* Chat Area / Zona Principal del Chat */}
      <div className="chat-area">
        {activeConversation ? (
          <>
            {/* Header del Chat */}
            <div className="chat-header">
              <span className="chat-header-title">{activeConversation.title}</span>
              <span className="chat-header-subtitle">Normativa UdeA</span>
            </div>

            {/* Historial de Mensajes */}
            <div className="messages-feed">
              {loading ? (
                <div style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
                  Cargando mensajes...
                </div>
              ) : messages.length === 0 ? (
                <div style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
                  Escribe un mensaje para comenzar la conversación.
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`message-wrapper ${msg.role === "user" ? "user" : "bot"}`}
                  >
                    {msg.role !== "user" && (
                      <div className="avatar bot" title="Asistente UdeA">
                        <GraduationCap size={18} />
                      </div>
                    )}
                    <div className="message-bubble">
                      <p style={{ whiteSpace: "pre-line" }}>{msg.content}</p>
                      <span className="message-time">
                        {new Date(msg.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                    {msg.role === "user" && (
                      <div className="avatar user" title="Usuario">
                        <User size={18} />
                      </div>
                    )}
                  </div>
                ))
              )}

              {/* Animación del Bot Escribiendo */}
              {isTyping && (
                <div className="message-wrapper bot">
                  <div className="avatar bot">
                    <GraduationCap size={18} />
                  </div>
                  <div className="message-bubble">
                    <div className="typing-indicator">
                      <span className="typing-dot"></span>
                      <span className="typing-dot"></span>
                      <span className="typing-dot"></span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Caja de Entrada de Texto */}
            <form className="input-area-container" onSubmit={handleSendMessage}>
              <div className="input-box-wrapper">
                <input
                  type="text"
                  className="chat-input"
                  placeholder="Escribe tu duda sobre reglamentos o acuerdos UdeA..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  disabled={isTyping}
                />
                <button
                  type="submit"
                  className="send-message-btn"
                  disabled={!inputValue.trim() || isTyping}
                >
                  <Send size={16} />
                </button>
              </div>
            </form>
          </>
        ) : (
          /* Estado Vacío (Sin chats seleccionados) */
          <div className="empty-state">
            <div className="empty-state-icon">
              <GraduationCap size={36} />
            </div>
            <h1 className="empty-state-title">Asistente Normativo UdeA</h1>
            <p className="empty-state-text">
              Bienvenido al asistente inteligente para la normativa de la Universidad de Antioquia.
              Selecciona una conversación existente o inicia una nueva en el menú de la izquierda para comenzar.
            </p>
            <button
              className="new-chat-btn"
              style={{ margin: "2rem auto 0" }}
              onClick={handleNewConversation}
            >
              <Plus size={18} />
              Iniciar nueva conversación
            </button>
          </div>
        )}
      </div>

      {/* Modal de Confirmación de Eliminación Personalizado (Estilo UdeA) */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={() => { setShowDeleteModal(false); setConversationToDelete(null); }}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Eliminar conversación</h3>
            <p className="modal-text">
              ¿Estás seguro de que deseas eliminar esta conversación? Esta acción borrará de forma permanente todo el historial de mensajes de este chat.
            </p>
            <div className="modal-actions">
              <button
                className="modal-btn secondary"
                onClick={() => { setShowDeleteModal(false); setConversationToDelete(null); }}
              >
                Cancelar
              </button>
              <button className="modal-btn danger" onClick={confirmDeleteConversation}>
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
