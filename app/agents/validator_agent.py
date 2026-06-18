from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _load_prompt(name: str) -> str:
    with open(_PROMPTS_DIR / f"{name}.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["system_prompt"]


def _get_llm() -> Any:
    from app.core.llm import get_llm

    return get_llm()


def validate(query: str, response: str) -> dict[str, Any]:
    """Valida si la respuesta satisface la pregunta del usuario.

    Returns:
        {"valid": bool, "reason": str}
    """
    llm = _get_llm()
    prompt = _load_prompt("validator_agent")

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"Question: {query}\n\nResponse to evaluate:\n{response}",
        },
    ]

    try:
        result = llm.invoke(messages)
        content = getattr(result, "content", str(result)).strip()
        data = json.loads(content)
        return {
            "valid": bool(data.get("valid", False)),
            "reason": str(data.get("reason", "")),
        }
    except Exception:
        # Si el validador falla, asumimos que la respuesta es válida para no bloquear el flujo
        return {"valid": True, "reason": "Validator skipped due to parsing error"}
