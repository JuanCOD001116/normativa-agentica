import logging
import os

from supabase import Client, create_client

logger = logging.getLogger(__name__)

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _client = create_client(url, key)
    return _client


def list_existing() -> set[str]:
    """Retorna el conjunto de codigos que ya existen en el bucket."""
    bucket = os.environ["SUPABASE_BUCKET"]
    files = _get_client().storage.from_(bucket).list()
    return {f["name"].removesuffix(".pdf") for f in files if f["name"].endswith(".pdf")}


def upload_pdf(codigo: str, content: bytes) -> str:
    """Sube un PDF al bucket. Retorna el path almacenado."""
    bucket = os.environ["SUPABASE_BUCKET"]
    path = f"{codigo}.pdf"

    _get_client().storage.from_(bucket).upload(
        path,
        content,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )
    logger.info("Uploaded %s to bucket '%s'.", path, bucket)
    return path
