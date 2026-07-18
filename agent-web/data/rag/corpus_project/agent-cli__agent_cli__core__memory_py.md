<!-- source: agent-cli/agent_cli/core/memory.py | title: memory.py -->

from dataclasses import dataclass, field

MAX_SHORT_TERM = 20
SUMMARIZE_AT = 16   # trigger summary when this many messages accumulated
KEEP_RECENT = 8     # how many recent messages to keep after summarizing


@dataclass
class Memory:
    short_term: list[dict] = field(default_factory=list)
    summary: str = ""
    working: dict = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        self.short_term.append({"role": role, "content": content})

    def needs_summary(self) -> bool:
        return len(self.short_term) >= SUMMARIZE_AT

    def take_old_for_summary(self) -> list[dict]:
        """Pop oldest messages for summarization; keep KEEP_RECENT recent ones."""
        if len(self.short_term) <= KEEP_RECENT:
            return []
        old = self.short_term[:-KEEP_RECENT]
        self.short_term = self.short_term[-KEEP_RECENT:]
        return old

    def pop_last_exchange(self) -> None:
        if len(self.short_term) >= 2:
            self.short_term = self.short_term[:-2]

    def get_messages(self) -> list[dict]:
        return list(self.short_term)

    @property
    def ctx_used(self) -> int:
        return len(self.short_term)

    def clear(self) -> None:
        self.short_term = []
        self.summary = ""
        self.working = {}
