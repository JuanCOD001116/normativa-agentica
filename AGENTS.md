# normativa-agentica

Python project for building regulatory/normative-oriented agents using LangGraph state-graph orchestration.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt  # includes requirements.txt
cp .env .env                         # fill secrets from .env template
```

- Virtual env is `venv/` (gitignored).
- `.env` contains secrets (gitignored).
- No `pyproject.toml` — uses `requirements.txt` + `requirements-dev.txt`.

## Commands

| Action | Command |
|---|---|
| Lint | `ruff check .` |
| Format | `ruff format .` |
| Typecheck | `mypy . --ignore-missing-imports` |
| Test | `pytest` |
| Ingest PDFs | `python -c "from app.core.ingest import ingest_all_from_docs; ingest_all_from_docs()"` |
| Query RAG | `python -c "from app.agents.rag_agent import ask; print(ask('tu pregunta'))"` |

## Project structure

```
main.py                  # LangGraph minimal demo
app/
  agents/
    rag_agent.py         # RAG agent: ask() with query rewriting
  core/
    embeddings.py        # Cohere embeddings (lazy-loaded)
    llm.py               # Ollama Cloud LLM (gemma4:31b)
    vector_store.py      # Supabase pgvector search
    chunking.py          # Article-aware PDF chunking
    ingest.py            # PDF ingestion pipeline
  prompts/
    rag_agent.yaml       # System prompt for RAG responses
    query_rewriter.yaml  # Prompt for query transformation
  tools/
  memory/
  api/
docs/
  reglamento_pregrado.pdf
  reglamento_posgrado.pdf
tests/
```

## Architecture

### RAG Pipeline

```
User question
  ↓
Query Rewriting (LLM rewrites for better retrieval)
  ↓
Embedding (Cohere embed-multilingual-v3.0)
  ↓
Supabase pgvector search (cosine similarity)
  ↓
Chunks + metadata (documento, artículo, capítulo)
  ↓
LLM generates response with citations (Ollama Cloud gemma4:31b)
```

### Key components

- **Embeddings**: Cohere `embed-multilingual-v3.0` (1024 dim). Uses `SecretStr.get_secret_value()` for API key.
- **LLM**: Ollama Cloud `gemma4:31b` via REST API with Bearer token.
- **Vector Store**: Supabase pgvector. Two RPC functions:
  - `match_documents` — filtered by document type
  - `match_documents_all` — searches all documents
- **Chunking**: Article-aware splitter. Each chunk starts with its article header.
- **Query Rewriting**: LLM transforms casual questions into formal academic queries.

### Search behavior

- If query contains "artículo N", fetches directly by metadata (exact match).
- Otherwise, uses semantic search via pgvector cosine similarity.
- When no document filter specified, uses `match_documents_all` (single RPC).

## Environment variables

```bash
# Cohere (embeddings)
COHERE_API_KEY=
COHERE_MODEL=embed-multilingual-v3.0

# Supabase (vector store)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

# Ollama Cloud (LLM)
OLLAMA_API_KEY=
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=gemma4:31b

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## Notable details

- **No pyproject.toml** — lint/format config relies on `ruff` defaults.
- **Secrets in `.env`** — never commit. Template is `.env` itself (fill values).
- **Cohere API key**: Must use `SecretStr(COHERE_API_KEY).get_secret_value()` — passing `SecretStr` directly causes 401 errors with langchain-cohide.
- **Supabase RPC**: `match_documents` has a bug with NULL filter from Python. Use `match_documents_all` when searching all documents.
- **Chunking**: Article-aware splitter ensures each chunk starts with "ARTÍCULO N." for better embedding quality.
- **Query Rewriting**: LLM rewrites casual questions into formal academic queries before embedding. Disable with `ask(query, use_rewrite=False)`.
