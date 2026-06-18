import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_cohere import CohereEmbeddings
from pydantic import SecretStr

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "")
COHERE_MODEL = os.environ.get("COHERE_MODEL", "embed-multilingual-v3.0")

_embeddings: CohereEmbeddings | None = None


def get_embeddings() -> CohereEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = CohereEmbeddings(  # type: ignore[call-arg]
            model=COHERE_MODEL,
            cohere_api_key=SecretStr(COHERE_API_KEY).get_secret_value()
            if COHERE_API_KEY
            else None,
        )
    return _embeddings
