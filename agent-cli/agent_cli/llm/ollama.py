from openai import OpenAI
from agent_cli.llm.base import OpenAICompatProvider
from agent_cli.config import OLLAMA_CHAT_URL


class OllamaProvider(OpenAICompatProvider):
    """Local Ollama, OpenAI-compatible endpoint. Always free (0₽)."""

    def __init__(self) -> None:
        self.client = OpenAI(api_key="ollama", base_url=OLLAMA_CHAT_URL)

    def _cost_rub(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        return 0.0
