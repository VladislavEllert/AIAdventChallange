from openai import OpenAI
from agent_cli.llm.base import OpenAICompatProvider, TokenUsageRef as _TokenUsageRef
from agent_cli.config import PROXYAPI_KEY, BASE_URL, calc_cost_rub


class ProxyAPIProvider(OpenAICompatProvider):
    def __init__(self) -> None:
        self.client = OpenAI(api_key=PROXYAPI_KEY, base_url=BASE_URL)

    def _cost_rub(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        return calc_cost_rub(prompt_tokens, completion_tokens, model)


class TokenUsageRef(_TokenUsageRef):
    """Back-compat: old call sites did TokenUsageRef(model) and got ProxyAPI pricing."""
    def __init__(self, model: str) -> None:
        super().__init__(model, calc_cost_rub)
