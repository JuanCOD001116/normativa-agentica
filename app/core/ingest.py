import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader

from app.core.chunking import split_regulatory_document
from app.core.embeddings import get_embeddings
from app.core.vector_store import _get_client, delete_by_documento

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "200"))


def ingest_document(pdf_path: str | Path, documento: str) -> int:
    """Ingesta un documento PDF al vector store de Supabase.

    Es idempotente: si ya existen chunks del mismo documento, los reemplaza.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"No se encontró el PDF: {pdf_path}")

    print(f"Cargando {pdf_path.name}...")
    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()
    print(f"  {len(pages)} páginas cargadas.")

    print(f"Dividiendo en chunks (documento: {documento})...")
    chunks = split_regulatory_document(
        pages=pages,
        documento=documento,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    print(f"  {len(chunks)} chunks generados.")

    print("Generando embeddings...")
    texts = [chunk.page_content for chunk in chunks]
    embedded_vectors = get_embeddings().embed_documents(texts)

    print("Eliminando chunks anteriores del mismo documento...")
    delete_by_documento(documento)

    print("Insertando en Supabase...")
    client = _get_client()
    rows = [
        {
            "content": chunk.page_content,
            "embedding": vector,
            "metadata": chunk.metadata,
        }
        for chunk, vector in zip(chunks, embedded_vectors)
    ]

    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.table("documents").insert(batch).execute()
        print(f"  Insertados {min(i + batch_size, len(rows))}/{len(rows)} chunks.")

    print(f"Ingesta completada: {len(rows)} chunks de '{documento}'.")
    return len(rows)


def _infer_document_type(filename: str) -> str:
    """Infiere el tipo de documento del nombre del archivo."""
    name_lower = filename.lower()
    if "pregrado" in name_lower:
        return "pregrado"
    if "posgrado" in name_lower:
        return "posgrado"
    return Path(filename).stem


def ingest_all_from_docs() -> dict[str, int]:
    """Escanea docs/ y procesa todos los PDFs encontrados.

    Infierre el tipo de documento del nombre del archivo:
    - 'reglamento_pregrado.pdf' → documento="pregrado"
    - 'reglamento_posgrado.pdf' → documento="posgrado"

    Returns:
        Dict con {nombre_documento: número_de_chunks}.
    """
    docs_dir = Path(__file__).resolve().parents[2] / "docs"
    pdfs = sorted(docs_dir.glob("*.pdf"))

    if not pdfs:
        print("No se encontraron PDFs en docs/")
        return {}

    results = {}
    for pdf in pdfs:
        documento = _infer_document_type(pdf.name)
        chunks = ingest_document(pdf, documento)
        results[documento] = chunks

    return results
