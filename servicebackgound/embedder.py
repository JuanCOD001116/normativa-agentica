import io
import json
import logging
import os

import cohere
import psycopg2
import pypdf

logger = logging.getLogger(__name__)

_COHERE_BATCH_SIZE = 96  # limite maximo de textos por llamada a Cohere


def extract_text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text: str) -> list[str]:
    size = int(os.getenv("CHUNK_SIZE", "1000"))
    overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def _embed(chunks: list[str]) -> list[list[float]]:
    co = cohere.Client(os.environ["COHERE_API_KEY"])
    model = os.environ["COHERE_MODEL"]
    embeddings: list[list[float]] = []

    for i in range(0, len(chunks), _COHERE_BATCH_SIZE):
        batch = chunks[i : i + _COHERE_BATCH_SIZE]
        response = co.embed(
            texts=batch,
            model=model,
            input_type="search_document",
        )
        embeddings.extend(response.embeddings)

    return embeddings


def _get_db_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def embed_and_store(pdf_bytes: bytes, metadata: dict) -> None:
    """Extrae texto, hace chunking, embeds con Cohere y guarda en tabla cache."""
    text = extract_text(pdf_bytes)
    if not text.strip():
        logger.warning("No text extracted for codigo %s. Skipping.", metadata.get("codigo"))
        return

    chunks = chunk_text(text)
    logger.info("Codigo %s: %d chunks generated.", metadata.get("codigo"), len(chunks))

    embeddings = _embed(chunks)

    conn = _get_db_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings):
                    vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    cur.execute(
                        """
                        INSERT INTO cache (content, embedding, metadata)
                        VALUES (%s, %s::vector, %s)
                        """,
                        (chunk, vector_str, json.dumps(metadata)),
                    )
    finally:
        conn.close()

    logger.info(
        "Stored %d chunks for codigo %s.", len(chunks), metadata.get("codigo")
    )
