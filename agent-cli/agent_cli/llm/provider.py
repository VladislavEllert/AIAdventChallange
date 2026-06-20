from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator
import time


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    elapsed_ms: float = 0.0
    cost_rub: float = 0.0

    def __str__(self) -> str:
        return (
            f"↑{self.prompt_tokens} ↓{self.completion_tokens} "
            f"= {self.total_tokens} tok  "
            f"{self.cost_rub:.4f}₽  "
            f"{self.elapsed_ms:.0f}ms"
        )


@dataclass
class SessionStats:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_rub: float = 0.0
    calls: int = 0

    def add(self, usage: TokenUsage) -> None:
        self.prompt_tokens += usage.prompt_tokens
        self.completion_tokens += usage.completion_tokens
        self.cost_rub += usage.cost_rub
        self.calls += 1

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], model: str, **kwargs) -> str:
        pass

    @abstractmethod
    def chat_stream(self, messages: list[dict], model: str, **kwargs) -> Iterator[str]:
        pass

    def chat_with_stats(self, messages: list[dict], model: str, **kwargs) -> tuple[str, TokenUsage]:
        """Default: calls chat() and measures time. No real token counts."""
        t0 = time.time()
        response = self.chat(messages, model, **kwargs)
        elapsed_ms = (time.time() - t0) * 1000
        return response, TokenUsage(elapsed_ms=elapsed_ms)
