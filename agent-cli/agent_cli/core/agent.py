from typing import Iterator
from agent_cli.llm.provider import LLMProvider, TokenUsage, SessionStats
from agent_cli.core.memory import Memory
from agent_cli.core.prompt_builder import build_system_prompt
from agent_cli.config import DEFAULT_MODEL

DEFAULT_PERSONA = (
    "Ты полезный ИИ-ассистент. Отвечай точно и по делу. "
    "У тебя есть история диалога с пользователем — используй её при ответах."
)

_SUMMARY_SYSTEM = (
    "Ты ассистент для сжатия переписки. "
    "Создай краткое резюме (2–4 предложения): ключевые факты, контекст, важные договорённости. "
    "Пиши только само резюме, без преамбул."
)


class Agent:
    def __init__(
        self,
        provider: LLMProvider,
        persona: str = DEFAULT_PERSONA,
        model: str = DEFAULT_MODEL,
        profile_content: str = "",
        invariants: list[str] | None = None,
    ) -> None:
        self.provider = provider
        self.persona = persona
        self.model = model
        self.profile_content = profile_content
        self.invariants = invariants or []
        self.memory = Memory()
        self.session_stats = SessionStats()

    def _build_messages(self, user_input: str, working_context: str = "") -> list[dict]:
        system = build_system_prompt(
            persona=self.persona,
            profile_content=self.profile_content,
            working_context=working_context,
            summary=self.memory.summary,
            invariants=self.invariants,
        )
        messages: list[dict] = [{"role": "system", "content": system}]
        messages.extend(self.memory.get_messages())
        messages.append({"role": "user", "content": user_input})
        return messages

    def _try_summarize(self) -> None:
        """Compress oldest messages into summary when context fills up."""
        if not self.memory.needs_summary():
            return
        old = self.memory.take_old_for_summary()
        if not old:
            return

        prev = (
            f"\n\nПредыдущее резюме:\n{self.memory.summary}"
            if self.memory.summary
            else ""
        )
        conv_text = "\n".join(
            f"{m['role'].upper()}: {m['content'][:400]}" for m in old
        )
        prompt = f"Сожми переписку в краткое резюме.{prev}\n\nПереписка:\n{conv_text}"

        new_summary = self.provider.chat(
            [
                {"role": "system", "content": _SUMMARY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            self.model,
            max_tokens=250,
        )
        self.memory.summary = (
            f"{self.memory.summary}\n\n{new_summary}" if self.memory.summary else new_summary
        )

    def respond(self, user_input: str, working_context: str = "") -> str:
        self._try_summarize()
        messages = self._build_messages(user_input, working_context)
        response = self.provider.chat(messages, self.model)
        self.memory.add_message("user", user_input)
        self.memory.add_message("assistant", response)
        return response

    def respond_with_stats(self, user_input: str, working_context: str = "") -> tuple[str, TokenUsage]:
        self._try_summarize()
        messages = self._build_messages(user_input, working_context)
        response, usage = self.provider.chat_with_stats(messages, self.model)
        self.session_stats.add(usage)
        self.memory.add_message("user", user_input)
        self.memory.add_message("assistant", response)
        return response, usage

    def respond_stream(self, user_input: str, working_context: str = "") -> Iterator[str]:
        self._try_summarize()
        messages = self._build_messages(user_input, working_context)
        full = ""
        for chunk in self.provider.chat_stream(messages, self.model):
            full += chunk
            yield chunk
        self.memory.add_message("user", user_input)
        self.memory.add_message("assistant", full)

    def respond_stream_with_stats(
        self, user_input: str, working_context: str = ""
    ) -> "tuple[Iterator[str], object]":
        """
        Returns (chunk_iter, stats_ref) for streaming with real token counts.
        Call list(chunk_iter) to drive it, then read stats_ref.usage.
        Only works if provider supports chat_stream_with_stats.
        """
        self._try_summarize()
        messages = self._build_messages(user_input, working_context)

        if hasattr(self.provider, "chat_stream_with_stats"):
            chunk_iter, ref = self.provider.chat_stream_with_stats(messages, self.model)

            def _tracked():
                full = ""
                for chunk in chunk_iter:
                    full += chunk
                    yield chunk
                self.memory.add_message("user", user_input)
                self.memory.add_message("assistant", full)
                usage = ref.usage
                self.session_stats.add(usage)

            return _tracked(), ref
        else:
            # Fallback: non-streaming
            response, usage = self.respond_with_stats(user_input, working_context)

            def _once():
                yield response

            class _Ref:
                def __init__(self, u):
                    self._u = u
                @property
                def usage(self):
                    return self._u

            return _once(), _Ref(usage)
