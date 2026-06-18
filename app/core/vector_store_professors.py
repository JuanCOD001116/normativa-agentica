import os

import cohere
import psycopg2
import psycopg2.extras


def _get_db_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def _embed_query(text: str) -> list[float]:
    co = cohere.Client(os.environ["COHERE_API_KEY"])
    model = os.environ["COHERE_MODEL"]
    response = co.embed(texts=[text], model=model, input_type="search_query")
    return response.embeddings[0]


def search_cache(query: str, k: int = 5) -> list[dict]:
    """Busca en la tabla cache usando similitud vectorial con pgvector."""
    embedding = _embed_query(query)
    vector_str = "[" + ",".join(str(x) for x in embedding) + "]"

    sql = """
        SELECT content, metadata, 1 - (embedding <=> %s::vector) AS similarity
        FROM cache
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    conn = _get_db_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (vector_str, vector_str, k))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "content": row["content"],
            "metadata": row["metadata"],
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]
