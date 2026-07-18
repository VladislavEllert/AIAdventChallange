<!-- source: agent-cli/agent_cli/llm/dispatch.py | title: dispatch.py -->

from agent_cli.llm.provider import LLMProvider
from agent_cli.llm.proxyapi import ProxyAPIProvider
from agent_cli.llm.ollama import OllamaProvider

OLLAMA_PREFIX = "ollama/"


class DispatchProvider(LLMProvider):
    """Routes chat calls to the right backend by model-id prefix.

    `ollama/qwen3:4b` -> OllamaProvider, model stripped to `qwen3:4b` (bare
    id Ollama expects). Anything else (`openai/...`, `gemini/...`) ->
    ProxyAPIProvider, model unchanged.
    """

    def __init__(self, proxyapi: LLMProvider | None = None, ollama: LLMProvider | None = None) -> None:
        # Both lazy: cloud models are hidden from the picker (local-only setup),
        # so ProxyAPIProvider must not construct eagerly — it raises if
        # PROXYAPI_KEY is unset/unusable, which would break local-only chat.
        self._proxyapi = proxyapi
        self._ollama = ollama

    @property
    def proxyapi(self) -> LLMProvider:
        if self._proxyapi is None:
            self._proxyapi = ProxyAPIProvider()
        return self._proxyapi

    @property
    def ollama(self) -> LLMProvider:
        if self._ollama is None:
            self._ollama = OllamaProvider()
        return self._ollama

    def resolve(self, model: str) -> tuple[LLMProvider, str]:
        if model.startswith(OLLAMA_PREFIX):
            return self.ollama, model[len(OLLAMA_PREFIX):]
        return self.proxyapi, model

    def client_for(self, model: str):
        """Raw OpenAI SDK client + bare model id, for call sites that bypass
        the LLMProvider methods (tool-calling, task-state extraction)."""
        provider, bare_model = self.resolve(model)
        return provider.client, bare_model

    def chat(self, messages: list[dict], model: str, **kwargs) -> str:
        provider, bare_model = self.resolve(model)
        return provider.chat(messages, bare_model, **kwargs)

    def chat_stream(self, messages: list[dict], model: str, **kwargs):
        provider, bare_model = self.resolve(model)
        return provider.chat_stream(messages, bare_model, **kwargs)

    def chat_with_stats(self, messages: list[dict], model: str, **kwargs):
        provider, bare_model = self.resolve(model)
        return provider.chat_with_stats(messages, bare_model, **kwargs)

    def chat_stream_with_stats(self, messages: list[dict], model: str, **kwargs):
        provider, bare_model = self.resolve(model)
        return provider.chat_stream_with_stats(messages, bare_model, **kwargs)
