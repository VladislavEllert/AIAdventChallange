<!-- source: agent-cli/agent_cli/profile/profile.py | title: profile.py -->

from pathlib import Path
from pydantic import BaseModel
import agent_cli.config as cfg


class UserProfile(BaseModel):
    name: str
    persona: str = ""
    style: str = ""
    rules: str = ""
    stack: str = ""
    interests: str = ""

    def to_prompt_text(self) -> str:
        parts: list[str] = []
        if self.persona:
            parts.append(f"## Профиль\n{self.persona}")
        if self.style:
            parts.append(f"## Стиль\n{self.style}")
        if self.rules:
            parts.append(f"## Правила/ограничения\n{self.rules}")
        if self.stack:
            parts.append(f"## Стек\n{self.stack}")
        if self.interests:
            parts.append(f"## Увлечения\n{self.interests}")
        return "\n\n".join(parts)

    def save(self) -> None:
        path = Path(cfg.PROFILES_DIR) / f"{self.name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._to_md(), encoding="utf-8")

    def _to_md(self) -> str:
        return (
            f"# Профиль: {self.name}\n\n"
            f"## Профиль\n{self.persona}\n\n"
            f"## Стиль\n{self.style}\n\n"
            f"## Правила/ограничения\n{self.rules}\n\n"
            f"## Стек\n{self.stack}\n\n"
            f"## Увлечения\n{self.interests}\n"
        )

    @classmethod
    def load(cls, name: str) -> "UserProfile":
        path = Path(cfg.PROFILES_DIR) / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found at {path}")
        return cls._parse_md(name, path.read_text(encoding="utf-8"))

    @classmethod
    def _parse_md(cls, name: str, content: str) -> "UserProfile":
        sections: dict[str, str] = {}
        current: str | None = None
        lines: list[str] = []
        for line in content.splitlines():
            if line.startswith("## "):
                if current is not None:
                    sections[current] = "\n".join(lines).strip()
                current = line[3:].strip()
                lines = []
            elif not line.startswith("# "):
                lines.append(line)
        if current is not None:
            sections[current] = "\n".join(lines).strip()
        return cls(
            name=name,
            persona=sections.get("Профиль", ""),
            style=sections.get("Стиль", ""),
            rules=sections.get("Правила/ограничения", ""),
            stack=sections.get("Стек", ""),
            interests=sections.get("Увлечения", ""),
        )

    @classmethod
    def list_all(cls) -> list[str]:
        d = Path(cfg.PROFILES_DIR)
        if not d.exists():
            return []
        return sorted(p.stem for p in d.glob("*.md"))
