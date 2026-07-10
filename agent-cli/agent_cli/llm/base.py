import time
from typing import Iterator
from agent_cli.llm.provider import LLMProvider, TokenUsage


class TokenUsageRef:
    """Mutable box filled after streaming completes."""
    def __init__(self, model: str, cost_fn) -> None:
        self.model = model
        self._cost_fn = cost_fn
        self.t0: float = 0.0
        self.elapsed_ms: float = 0.0
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0

    @property
    def usage(self) -> TokenUsage:
        cost = self._cost_fn(self.prompt_tokens, self.completion_tokens, self.model)
        return TokenUsage(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            elapsed_ms=self.elapsed_ms,
            cost_rub=cost,
        )


class OpenAICompatProvider(LLMProvider):
    """Base for any OpenAI-compatible chat endpoint (ProxyAPI, Ollama, ...).

    Subclasses construct `self.client` (an `openai.OpenAI` instance, kept in the
    subclass's own module so call sites can patch `<module>.OpenAI` as before)
    and implement `_cost_rub`.
    """

    client: "object"

    def _cost_rub(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        raise NotImplementedError

    def chat(self, messages: list[dict], model: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def chat_with_stats(self, messages: list[dict], model: str, **kwargs) -> tuple[str, TokenUsage]:
        t0 = time.time()
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        elapsed_ms = (time.time() - t0) * 1000

        content = response.choices[0].message.content or ""
        usage = response.usage
        if usage:
            prompt_tok = usage.prompt_tokens
            completion_tok = usage.completion_tokens
            total_tok = usage.total_tokens
        else:
            prompt_tok = completion_tok = total_tok = 0

        cost = self._cost_rub(prompt_tok, completion_tok, model)
        return content, TokenUsage(
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=total_tok,
            elapsed_ms=elapsed_ms,
            cost_rub=cost,
        )

    def chat_stream(self, messages: list[dict], model: str, **kwargs) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def chat_stream_with_stats(
        self, messages: list[dict], model: str, **kwargs
    ) -> tuple[Iterator[str], "TokenUsageRef"]:
        """
        Returns (chunk_iterator, stats_ref).
        Consume the iterator fully, then read stats_ref.usage for TokenUsage.
        Uses stream_options include_usage to get real token counts from API.
        """
        ref = TokenUsageRef(model, self._cost_rub)

        def _gen():
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                **kwargs,
            )
            ref.t0 = time.time()
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                # Last chunk carries usage when include_usage=True
                if hasattr(chunk, "usage") and chunk.usage:
                    u = chunk.usage
                    ref.prompt_tokens = u.prompt_tokens
                    ref.completion_tokens = u.completion_tokens
                    ref.total_tokens = u.total_tokens
            ref.elapsed_ms = (time.time() - ref.t0) * 1000

        return _gen(), ref
