<!-- source: week-02/day-09/README.md | title: README.md -->

# День 9 — Управление контекстом: сжатие истории

> ⭐ **Главный код задания:**
> - **[Agent.swift](../../AgentChat/AgentChat/Agent/Agent.swift)** — `composedSystem()`: подстановка `summary` в `system` вместо полной истории.
> - **[ChatViewModel.swift](../../AgentChat/AgentChat/ViewModels/ChatViewModel.swift)** — `compressIfNeeded()` (старое → summary по числу сообщений), `compactNow()` (по токен-лимиту), окно N, тумблер `summaryEnabled`.
> - **[MemoryService.swift](../../AgentChat/AgentChat/Services/MemoryService.swift)** — `summarize()`: сжатие старого в summary.
> - **[ChatSession.swift](../../AgentChat/AgentChat/Models/ChatSession.swift)** — `summary` хранится отдельно в SQLite.

> ▶ **Видео:** https://www.loom.com/share/cbeff47284d641ad913540f47d3b14e1

Продолжение приложения [AgentChat](../../AgentChat/). Развивает память дня-7 и токены дня-8.

## Задача

Хранить последние N сообщений «как есть», остальное заменять `summary`, summary хранить
отдельно и подставлять в запрос вместо полной истории. Сравнить качество и расход токенов
без сжатия и со сжатием.

## Что сделано

- **Окно последних N «как есть».** В модель уходит окно из последних N сообщений
  (размер N — в настройках). Старое за окно — не шлётся целиком.
- **Старое → summary.** Когда история переросла N (или подошла к токен-лимиту) — старое
  начало сворачивается в `summary` дешёвой моделью. В чате видна плашка `Контекст сжат… → summary`.
- **Summary хранится отдельно** (`ChatSession.summary`, SQLite) и **подставляется в `system`
  вместо полной истории** — в модель идёт `персона + факты + summary + окно N`, а не весь диалог.
- **Сравнение без/со сжатием.** Тумблер **«Сжатие истории (summary)»** в настройках:
  - выкл → в модель идёт ВСЯ история (дороже, помнит дословно);
  - вкл → окно + summary (дешевле, суть держится, детали выборочно теряются).
- **Токены до/после** видны под каждым ответом (`↑вход`) и в HUD/«Статистике чата»:
  со сжатием вход (prompt) заметно ниже.

## Значимый код (для проверяющих)

- [`Agent.swift`](../../AgentChat/AgentChat/Agent/Agent.swift) — `composedSystem()`: подстановка `summary` в `system` вместо полной истории.
- [`ChatViewModel.swift`](../../AgentChat/AgentChat/ViewModels/ChatViewModel.swift) — `compressIfNeeded()` (старое → summary по числу сообщений), `compactNow()` (по токен-лимиту), окно N, тумблер `summaryEnabled`.
- [`MemoryService.swift`](../../AgentChat/AgentChat/Services/MemoryService.swift) — `summarize()`: сжатие старого в summary (бюджет слов по степени сжатия).
- [`ChatSession.swift`](../../AgentChat/AgentChat/Models/ChatSession.swift) — `summary` хранится отдельно в SQLite.
- [`SettingsView.swift`](../../AgentChat/AgentChat/Views/SettingsView.swift) — тумблер «Сжатие истории (summary)» + степень сжатия.
- [`ChatStatsSheet.swift`](../../AgentChat/AgentChat/Views/ChatStatsSheet.swift) — активное окно, что сжато, текущая summary.

## Как проверить

Один диалог прогнать дважды (одинаковые сообщения):
1. **Без сжатия** (тумблер выкл): вход (prompt) и Σток/₽ растут каждый ход, на вопрос из начала
   отвечает дословно — но дорого.
2. **Со сжатием** (тумблер вкл, окно N=4–6): после N сообщений идут плашки `Контекст сжат… → summary`,
   вход (prompt) держится низко, на вопрос отвечает по summary — дёшево, детали выборочно теряются.

## Вывод

Храним последние N + summary старого → в модель уходит мало токенов вместо всей истории →
дешевле. Суть длинного диалога держится в summary (лоссово, избирательно). Экономия токенов ↔
потеря части деталей — баланс, которым управляем.
