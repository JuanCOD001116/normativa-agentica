import json
import logging
import os

import cohere
import psycopg2

from servicebackgound.chunker import chunk_pdf

logger = logging.getLogger(__name__)

_COHERE_BATCH_SIZE = 96


def _embed(texts: list[str]) -> list[list[float]]:
    co = cohere.Client(os.environ["COHERE_API_KEY"])
    model = os.environ["COHERE_MODEL"]
    embeddings: list[list[float]] = []

    for i in range(0, len(texts), _COHERE_BATCH_SIZE):
        batch = texts[i : i + _COHERE_BATCH_SIZE]
        response = co.embed(texts=batch, model=model, input_type="search_document")
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
    """Divide el PDF por artículos, embeds con Cohere y guarda en tabla cache."""
    chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
    chunks = chunk_pdf(pdf_bytes, chunk_size=chunk_size)

    if not chunks:
        logger.warning(
            "No text extracted for codigo %s. Skipping.", metadata.get("codigo")
        )
        return

    logger.info("Codigo %s: %d chunks generated.", metadata.get("codigo"), len(chunks))

    embeddings = _embed([c.text for c in chunks])

    conn = _get_db_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings):
                    vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    chunk_metadata = {
                        **metadata,
                        "articulo": chunk.articulo,
                        "capitulo": chunk.capitulo,
                        "page": chunk.page,
                    }
                    cur.execute(
                        "INSERT INTO cache (content, embedding, metadata) VALUES (%s, %s::vector, %s)",
                        (chunk.text, vector_str, json.dumps(chunk_metadata)),
                    )
    finally:
        conn.close()

    logger.info("Stored %d chunks for codigo %s.", len(chunks), metadata.get("codigo"))
