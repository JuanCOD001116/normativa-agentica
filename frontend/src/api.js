const BASE_URL = "/api";

export const getOrCreateUserId = () => {
  let userId = localStorage.getItem("user_id");
  if (!userId) {
    // Generar un ID único simple para el usuario
    userId = `usr_${Math.random().toString(36).substring(2, 11)}_${Date.now()}`;
    localStorage.setItem("user_id", userId);
  }
  return userId;
};

export const api = {
  // Obtener todas las conversaciones de un usuario
  async getConversations(userId) {
    const response = await fetch(`${BASE_URL}/conversations/?user_id=${encodeURIComponent(userId)}`);
    if (!response.ok) {
      throw new Error("Error al obtener las conversaciones");
    }
    return response.json();
  },

  // Crear una nueva conversación
  async createConversation(userId, title = "Nueva conversación") {
    const response = await fetch(`${BASE_URL}/conversations/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        title: title,
      }),
    });
    if (!response.ok) {
      throw new Error("Error al crear la conversación");
    }
    return response.json();
  },

  // Obtener el detalle de una conversación (incluye mensajes)
  async getConversationDetail(conversationId) {
    const response = await fetch(`${BASE_URL}/conversations/${conversationId}`);
    if (!response.ok) {
      throw new Error("Error al obtener el detalle de la conversación");
    }
    return response.json();
  },

  // Agregar un mensaje a una conversación
  async sendMessage(conversationId, role, content, meta_data = null) {
    const response = await fetch(`${BASE_URL}/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        role,
        content,
        meta_data,
      }),
    });
    if (!response.ok) {
      throw new Error("Error al enviar el mensaje");
    }
    return response.json();
  },

  // Eliminar una conversación
  async deleteConversation(conversationId) {
    const response = await fetch(`${BASE_URL}/conversations/${conversationId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Error al eliminar la conversación");
    }
    return true;
  },

  // Actualizar el título de la conversación
  async updateConversation(conversationId, title, metaData = null) {
    const response = await fetch(`${BASE_URL}/conversations/${conversationId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title,
        meta_data: metaData,
      }),
    });
    if (!response.ok) {
      throw new Error("Error al actualizar la conversación");
    }
    return response.json();
  },
};
