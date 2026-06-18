# normativa-agentica

Proyecto Python para construir agentes orientados a normativa usando orquestacion por grafos de estado, RAG sobre documentos internos, consulta web en vivo y una API conversacional.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
```

- El entorno virtual local esperado es `venv/` y no debe versionarse.
- Los secretos van en `.env` y no deben versionarse.
- Si existe `.env.example`, debe mantenerse como plantilla sin secretos reales.
- No hay `pyproject.toml`; el proyecto usa `requirements.txt` y `requirements-dev.txt`.

## Commands

| Action | Command |
|---|---|
| Lint Python | `ruff check .` |
| Format Python | `ruff format .` |
| Typecheck Python | `mypy . --ignore-missing-imports` |
| Test Python | `pytest` |
| Run FastAPI | `python -m app.api.main` |
| Run API with uvicorn | `uvicorn app.api.main:app --reload` |
| Run orchestrator demo | `python app/agents/orchestrator.py` |
| Ingest bundled PDFs | `python -c "from app.core.ingest import ingest_all_from_docs; ingest_all_from_docs()"` |
| Query RAG | `python -c "from app.agents.rag_agent import ask; print(ask('tu pregunta'))"` |
| Frontend install | `cd frontend && npm install` |
| Frontend dev server | `cd frontend && npm run dev` |
| Frontend build | `cd frontend && npm run build` |
| Frontend lint | `cd frontend && npm run lint` |
| Background ingestion debug | `set SERVICE_RUN_MODE=debug && python -m servicebackgound.main` |

## Project structure

```txt
main.py                         # LangGraph minimal demo
app/
  agents/
    orchestrator.py             # Routes queries to document or web agents
    rag_agent.py                # RAG agent: ask() with optional query rewriting
  api/
    main.py                     # FastAPI app
    routes/conversations.py     # Conversation and message endpoints
  core/
    agent.py                    # Core agent helpers
    chunking.py                 # Article-aware PDF chunking
    database.py                 # SQLAlchemy database/session setup
    embeddings.py               # Cohere embeddings (lazy-loaded)
    ingest.py                   # PDF ingestion pipeline
    llm.py                      # Ollama Cloud LLM client
    models.py                   # SQLAlchemy models
    schemas.py                  # Pydantic schemas
    services.py                 # Conversation/message service layer
    vector_store.py             # Supabase pgvector search
  prompts/
    rag_agent.yaml              # System prompt for RAG responses
    query_rewriter.yaml         # Prompt for query transformation
  tools/
  memory/
docs/
  reglamento_pregrado.pdf
  reglamento_posgrado.pdf
  orchestrator-implementation.md
  stack-recomendado.md
frontend/                       # React + Vite UI
servicebackgound/               # Scheduled ingestion service
tests/
```

Note: `servicebackgound` is the current package name in the repository. Keep imports consistent with that spelling unless the package is renamed everywhere in one coordinated change.

## Architecture

### Target flow

```txt
User question
  -> Orchestrator
  -> Route to document agent or web/scraping agent
  -> Retrieve evidence from vector store or live source
  -> Validate grounding, citation, and relevance
  -> Return final answer or low-confidence notice
```

### RAG pipeline

```txt
User question
  -> Query rewriting
  -> Embedding with Cohere embed-multilingual-v3.0
  -> Supabase pgvector search
  -> Chunks + metadata (documento, articulo, capitulo)
  -> LLM response with citations
```

### Key components

- **Orchestrator**: `app/agents/orchestrator.py` routes by keywords with heuristic fallback. Current agent calls are mocks unless injected through `orchestrate_with_components`.
- **RAG Agent**: `app/agents/rag_agent.py` answers document questions using retrieval and citations. Query rewriting can be disabled with `ask(query, use_rewrite=False)`.
- **Embeddings**: Cohere `embed-multilingual-v3.0` with 1024 dimensions.
- **LLM**: Ollama Cloud model configured by `OLLAMA_MODEL`.
- **Vector Store**: Supabase pgvector with RPC functions `match_documents` and `match_documents_all`.
- **API**: FastAPI app in `app/api/main.py`, with conversation endpoints under `/api`.
- **Frontend**: React + Vite app in `frontend/`.
- **Background service**: `servicebackgound/main.py` can run ingestion immediately in debug mode or on a cron schedule.

## Search behavior

- If the query contains `articulo N`, the RAG path can fetch directly by metadata.
- Otherwise, semantic search uses pgvector cosine similarity.
- When no document filter is specified, use `match_documents_all` instead of passing a null filter to `match_documents`.

## Environment variables

```bash
# Cohere
COHERE_API_KEY=
COHERE_MODEL=embed-multilingual-v3.0

# Supabase / vector store
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

# Ollama Cloud
OLLAMA_API_KEY=
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=gemma4:31b

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# API / relational database
DATABASE_URL=

# Background service
SERVICE_RUN_MODE=scheduled
SERVICE_CRON_EXPRESSION=0 1 * * *
```

## Development notes

- Never commit `.env`, API keys, service keys, local databases, build artifacts, or `venv/`.
- Prefer existing module boundaries: agents in `app/agents`, API routes in `app/api`, business logic in `app/core/services.py`, schemas in `app/core/schemas.py`.
- Use dependency injection where the orchestrator already supports it instead of hard-wiring future agents.
- Keep tests focused. API behavior currently has coverage in `tests/test_conversations.py` using an in-memory SQLite database.
- The codebase currently contains some Windows/encoding artifacts in comments and docs. When touching files, preserve behavior and clean text only in the edited area.

## Notable details

- Cohere API keys should be passed as plain secret strings. If wrapped in `SecretStr`, call `.get_secret_value()` before handing the key to the client.
- Supabase RPC `match_documents` has a known null-filter issue from Python; use `match_documents_all` when searching all documents.
- Article-aware chunking should keep each chunk anchored to its `ARTICULO N.` header for better retrieval quality.
- Query rewriting converts casual Spanish questions into more formal academic/normative queries before embedding.
