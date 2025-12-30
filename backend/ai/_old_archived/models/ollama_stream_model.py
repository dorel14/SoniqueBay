# backend/ai_agents/models/ollama_stream_model.py

from typing import AsyncGenerator, Optional
import httpx
from pydantic_ai.models import Model


class OllamaStreamModel(Model):
    """
    Backend PydanticAI avec support streaming pour Ollama.
    """
    def __init__(self, model_name: str, api_url="http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.api_url = api_url

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Streaming token-par-token depuis Ollama.
        """
        async with httpx.AsyncClient(timeout=None) as client:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
            }

            async with client.stream("POST", self.api_url, json=payload) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = httpx.Response(200, content=line).json()
                        token = data.get("response", "")
                        if token:
                            yield token
                    except Exception:
                        continue

    async def run(self, prompt: str) -> str:
        """
        Version NON-streaming requise par PydanticAI.
        """
        chunks = []
        async for tok in self.stream(prompt):
            chunks.append(tok)
        return "".join(chunks)
