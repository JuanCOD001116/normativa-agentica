import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

_llm: ChatOllama | None = None


def get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        _llm = ChatOllama(
            model=os.environ.get("OLLAMA_MODEL", "gemma4:31b"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "https://ollama.com"),
            client_kwargs={
                "headers": {
                    "Authorization": f"Bearer {os.environ.get('OLLAMA_API_KEY', '')}"
                }
            },
        )
    return _llm
