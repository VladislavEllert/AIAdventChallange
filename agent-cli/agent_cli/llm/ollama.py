import httpx
from openai import OpenAI
from agent_cli.llm.base import OpenAICompatProvider
from agent_cli.config import OLLAMA_CHAT_URL

# connect fast-fails (box asleep / unreachable) — no reason to wait long for a
# TCP handshake on a LAN. read is generous: Qwen3's <think> reasoning can
# legitimately run 30-60s+ before the first token (day 28 finding) — without
# this the OpenAI SDK's default ~600s timeout meant an unreachable box hung
# the whole chat silently for up to 10 minutes before anything surfaced.
_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)


class OllamaProvider(OpenAICompatProvider):
    """Local Ollama, OpenAI-compatible endpoint. Always free (0₽)."""

    def __init__(self) -> None:
        # max_retries=0: this is a LAN box, not flaky internet — the SDK's
        # default of 2 retries turned one 5s connect-timeout into a ~16s wait
        # (3 attempts) before anything surfaced to the user.
        # trust_env=False on the http_client: on Windows with a system SOCKS
        # proxy configured (VPN software), httpx otherwise tries to route this
        # local/LAN call through it and fails with "Unknown scheme for proxy
        # URL socks4://...". Ollama is always local/LAN — never needs a proxy.
        self.client = OpenAI(
            api_key="ollama",
            base_url=OLLAMA_CHAT_URL,
            max_retries=0,
            http_client=httpx.Client(timeout=_TIMEOUT, trust_env=False),
        )

    def _cost_rub(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        return 0.0
