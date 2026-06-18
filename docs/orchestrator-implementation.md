# Orquestador - Implementación y Guía de Integración

## Descripción General

El orquestador es el componente central que enruta consultas del usuario hacia el agente especializado correcto:
- **AG_DOC** (Agente de Documentos): para consultas sobre reglamento interno
- **AG_SCRAPE** (Agente de Scraping): para consultas de normativa web en vivo

El orquestador está diseñado para ser modular y permite la integración progresiva de componentes.

---

## Archivo Principal

**Ubicación:** `app/agents/orchestrator.py`

Contiene toda la lógica de routing y dos entry points:
- `orchestrate(query)` - Versión actual con mocks (para testing)
- `orchestrate_with_components(query, agent_doc_fn, agent_web_fn)` - Versión inyectable (para componentes reales)

---

## Cómo funciona el Routing

### 1. Detección por Palabras Clave

El orquestador primero analiza la consulta buscando palabras clave específicas:

**Palabras clave para AG_DOC (Documentos):**
- reglamento, documento, interno, política, procedimiento, normativo, manual, guía

**Palabras clave para AG_SCRAPE (Web):**
- web, normativa, vivo, actual, consulta, en línea, online, corriente

**Ejemplo:**
```
"¿Cuál es el reglamento interno sobre permisos?"
→ Palabra clave "reglamento" detectada
→ Routing a AG_DOC
```

### 2. Fallback con Análisis Ligero (LLM)

Si la detección por keywords es ambigua, usa una heurística simple:
- Preguntas interrogativas amplias (cuál, dónde, cuándo, etc.) → AG_SCRAPE
- Resto de consultas → AG_DOC (default)

**Ejemplo:**
```
"¿Cómo funciona la solicitud de permisos?"
→ Sin palabras clave específicas
→ Heurística: Pregunta con "cómo" → AG_DOC
```

---

## Interfaces Esperadas

Cuando otros equipos tengan listos sus componentes, deben implementar estas signaturas exactas:

### Agente de Documentos (AG_DOC)

```python
def agent_documents(query: str) -> Dict[str, Any]:
    """
    Consulta el vector store con embeddings del reglamento interno.
    
    Args:
        query: Pregunta del usuario
    
    Returns:
        Dict con estructura:
        {
            "response": "Respuesta encontrada en los documentos",
            "sources": ["doc1.pdf", "doc2.pdf"],
            "confidence": 0.85,
            # Campos adicionales permitidos
        }
    """
```

### Agente de Scraping (AG_SCRAPE)

```python
def agent_scraping(query: str) -> Dict[str, Any]:
    """
    Consulta normativa.udea.edu.co en vivo.
    
    Args:
        query: Pregunta del usuario
    
    Returns:
        Dict con estructura:
        {
            "response": "Respuesta obtenida de la web",
            "url": "https://normativa.udea.edu.co/consulta",
            "date_fetched": "2026-06-17",
            # Campos adicionales permitidos
        }
    """
```

---

## Integración de Componentes Reales

### Paso 1: Implementar el Agente

Crear archivo `app/agents/doc_agent.py` (o `web_agent.py`):

```python
# app/agents/doc_agent.py

from typing import Any, Dict

def agent_documents(query: str) -> Dict[str, Any]:
    """Tu implementación real del Agente de Documentos"""
    # Tu código aquí con ChromaDB, RAG, etc.
    return {
        "response": "Tu respuesta aquí",
        "sources": ["..."],
        "confidence": 0.9
    }
```

### Paso 2: Usar `orchestrate_with_components()`

En tu código (o API):

```python
from app.agents import orchestrate_with_components
from app.agents.doc_agent import agent_documents
from app.agents.web_agent import agent_scraping

# Llamar al orquestador con tus componentes reales
result = orchestrate_with_components(
    query="¿Cuál es el reglamento sobre vacaciones?",
    agent_doc_fn=agent_documents,
    agent_web_fn=agent_scraping
)

print(result)
# {
#     "agent": "doc",
#     "query": "¿Cuál es el reglamento sobre vacaciones?",
#     "routing_reason": "Detectada palabra clave de documento interno",
#     "response": "Las vacaciones se regulan según...",
#     "agent_details": {...}
# }
```

---

## Ejemplos de Uso

### Uso Actual (con Mocks)

```python
from app.agents import orchestrate

result = orchestrate("¿Qué dice el reglamento sobre permisos?")
print(result["agent"])         # "doc"
print(result["response"])      # "[MOCK AG_DOC] Respuesta simulada..."
print(result["routing_reason"]) # "Detectada palabra clave de documento interno"
```

### Solo Routing (sin Agentes)

```python
from app.agents import route_query

routing = route_query("¿Dónde encuentro normativa vigente?")
print(routing["agent"])   # "web"
print(routing["reason"])  # "Detectada palabra clave de normativa web"
```

### Con Componentes Reales (Futuro)

```python
from app.agents import orchestrate_with_components
from app.agents.doc_agent import agent_documents
from app.agents.web_agent import agent_scraping

result = orchestrate_with_components(
    query="Tu pregunta aquí",
    agent_doc_fn=agent_documents,
    agent_web_fn=agent_scraping
)
```

---

## Estructura de Datos

### Input

```python
{
    "query": "¿Cuál es el reglamento sobre permisos?",
    "user_id": "optional",           # Opcional
    "context": {}                     # Opcional, para multi-turn
}
```

### Output

```python
{
    "agent": "doc",                              # Tipo de agente enrutado
    "query": "¿Cuál es el reglamento sobre...?", # Pregunta original
    "routing_reason": "Detectada palabra clave de documento interno",
    "response": "Respuesta del agente",          # Respuesta principal
    "agent_details": {
        "response": "...",
        "sources": ["..."],
        "confidence": 0.85,
        # Contenido adicional del agente
    }
}
```

---

## Testing

### Ejecutar Tests del Orquestador

```bash
cd /workspaces/normativa-agentica
python app/agents/orchestrator.py
```

Genera salida como:
```
================================================================================
TESTS DEL ORQUESTADOR - SISTEMA DE NORMATIVA
================================================================================

--- Prueba 1: Orquestador con Mocks ---

[ORCHESTRATOR] Recibida pregunta: '¿Cuál es el reglamento interno sobre permisos?'
[ORCHESTRATOR] Routing: doc (Detectada palabra clave de documento interno)
[ORCHESTRATOR] Respuesta del agente: [MOCK AG_DOC] Respuesta del Agente de Documentos...
```

---

## Exports Públicas

Desde `app/agents/__init__.py`:

```python
from app.agents import (
    AGENT_DOCUMENTS,              # Constante: "doc"
    AGENT_SCRAPING,               # Constante: "web"
    orchestrate,                  # Función con mocks
    orchestrate_with_components,  # Función inyectable
    route_query,                  # Solo routing
)
```

---

## Decisiones de Diseño

| Aspecto | Decisión | Razón |
|---------|----------|-------|
| **Funciones** | Simples, no clases | Fácil integración sin acoplamiento |
| **Mocks** | Hardcodeados | Testing sin dependencias externas |
| **Contrato** | Dicts simples | Flexible, sin Pydantic overhead |
| **Logging** | Print simple | Debugging rápido en desarrollo |

---

## Checklist para Integración

Cuando tu agente esté listo:

- [ ] Implementaste la función con la firma exacta especificada
- [ ] Retorna un Dict con al menos campo `"response"`
- [ ] Probaste localmente: `orchestrate_with_components(query, tu_func, mock)`
- [ ] Sin dependencias circulares
- [ ] Documentaste cualquier variable de entorno necesaria en `.env.example`

---

## Notas y Limitaciones

1. **Sin Validador por ahora**: El orquestador NO valida respuestas. Eso viene después.
2. **Routing es heurístico**: Usa keywords + fallback simple. Si necesitas LLM real, reemplaza `detect_agent_by_llm()`.
3. **Print vs Logging**: Usa print por simplicidad. Para producción, reemplaza con `logging` o `structlog`.

---

## Contacto y Soporte

Si tienes dudas sobre:
- Estructura del Dict esperado → Ve `Estructura de Datos` arriba
- Cómo integrar tu componente → Ve `Integración de Componentes Reales`
- Errores en tests → Ejecuta `python app/agents/orchestrator.py` y revisa output

