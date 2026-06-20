def build_system_prompt(
    persona: str,
    profile_content: str = "",
    working_context: str = "",
    summary: str = "",
    invariants: list[str] | None = None,
) -> str:
    parts = [persona]

    if profile_content:
        parts.append(f"# Профиль пользователя\n{profile_content}")

    if summary:
        parts.append(f"# Резюме предыдущего контекста\n{summary}")

    if working_context:
        parts.append(f"# Рабочий контекст задачи\n{working_context}")

    if invariants:
        inv_text = "\n".join(f"- {inv}" for inv in invariants)
        parts.append(
            f"# [ИНВАРИАНТЫ] — нарушение ЗАПРЕЩЕНО, нет исключений\n{inv_text}"
        )

    return "\n\n".join(parts)
