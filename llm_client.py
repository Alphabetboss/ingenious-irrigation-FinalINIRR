import os
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


class LLMError(RuntimeError):
    pass


def local_chat(prompt: str, model: str = "phi3.5:3.8b-mini-instruct-q4_K_M", *, timeout=120) -> str:
    """Send a single, non-streaming prompt to the local Ollama HTTP API and return the text response."""
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",
            },
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data["response"]
    except Exception as e:
        raise LLMError(f"LLM call failed: {e}") from e

