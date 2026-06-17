# normativa-agentica

Proyecto para construir agentes orientados a normativa, con orquestacion por grafo de estados y rutas especializadas para documentos internos y consulta web en vivo.

## Arquitectura objetivo

El sistema separa responsabilidades por tipo de consulta y valida la calidad de la respuesta antes de entregarla al usuario.

```mermaid
flowchart TD
		UI[Interfaz de usuario<br/>Streamlit / Gradio / Chainlit]
		ORQ[Orquestador<br/>LangGraph - grafo de estados]
		AG_DOC[Agente de documentos<br/>RAG sobre reglamento]
		AG_SCRAPE[Agente de scraping<br/>Consulta HTML en vivo]
		VS[(Vector store<br/>Embeddings reglamento)]
		WEB[(normativa.udea.edu.co<br/>Consultar / ExtensionDocumento / Documento)]
		VAL{Validador<br/>Fundamentacion + cita + relevancia}
		RESP[Respuesta final<br/>o aviso de baja confianza]

		UI --> ORQ
		ORQ -->|ruta documentos| AG_DOC
		ORQ -->|ruta normativa web| AG_SCRAPE
		AG_DOC --> VS
		AG_SCRAPE --> WEB
		VS --> VAL
		WEB --> VAL
		VAL -->|rechaza, feedback| ORQ
		VAL -->|aprueba| RESP
		RESP --> UI

		linkStyle 6 stroke-dasharray: 4 3
```

## Patrones arquitectonicos

- Patron orquestador y subagentes.
- Patron supervisor.
- Agentes como tools.

## Stack recomendado para desarrollo y produccion

### Objetivo del entorno

- Crear agentes modulares y extensibles.
- Probar flujos localmente con trazas claras.
- Gestionar configuracion por entorno sin secretos en codigo.
- Escalar a API/servicio productivo sin rehacer la base.

### Dependencias base

#### Orquestacion y agentes

- langchain
- langgraph
- langchain-openai (u otro proveedor)
- langchain-community

#### Configuracion y validacion

- python-dotenv
- pydantic
- pydantic-settings

#### Desarrollo y calidad

- rich
- pytest
- pytest-asyncio
- ruff
- mypy

### Produccion

#### API y ejecucion

- fastapi
- uvicorn
- gunicorn (opcional segun despliegue)

#### Observabilidad

- langsmith
- logging estandar o structlog
- opentelemetry-api y opentelemetry-sdk

#### Persistencia y estado

- sqlalchemy
- alembic
- sqlite en desarrollo
- postgresql en produccion

#### Memoria y busqueda vectorial

- chromadb para prototipos
- faiss-cpu para uso local de alto rendimiento
- pgvector cuando se trabaja con PostgreSQL

### Utilidades opcionales

- httpx
- tenacity
- cachetools
- orjson
- typer
- docker

## Estructura sugerida

```txt
app/
	agents/
	tools/
	prompts/
	memory/
	api/
	core/
tests/
docs/
.env.example
main.py
pyproject.toml
README.md
```

## Mejores practicas

- Mantener configuracion en variables de entorno.
- Separar agentes, tools y prompts por modulos.
- Validar entradas y salidas con pydantic.
- Implementar pruebas unitarias por tool y por flujo.
- Instrumentar trazas desde el inicio.
- Empezar con pocas dependencias y crecer por necesidad.
- Documentar secretos requeridos en .env.example.
- Fijar versiones cuando el sistema entre en fase estable.

## Arranque minimo recomendado

Base inicial para comenzar rapido:

- langchain
- langgraph
- python-dotenv
- pydantic
- pytest
- ruff
- rich
Documento de detalle adicional: [docs/stack-recomendado.md](docs/stack-recomendado.md)
