
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")  # docker-compose
DEFAULT_OLLAMA_MODEL = os.getenv("AGENT_MODEL", "phi3:mini")


def get_ollama_model(
    model_name: str,
    num_ctx: int = 4096
):
    return OpenAIChatModel(
        model_name=DEFAULT_OLLAMA_MODEL,
        provider=OllamaProvider(base_url=OLLAMA_BASE_URL),
        max_context_length=num_ctx
    )
