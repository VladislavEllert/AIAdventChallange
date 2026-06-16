# День 11 — Модель памяти ассистента (memory layers)

> ⭐ **Главный код задания:**
> - **[Agent.swift](../../AgentChat/AgentChat/Agent/Agent.swift)** — `composedSystem()`: сборка промпта из 3 слоёв памяти (глобальный профиль → рабочая память → summary → окно сообщений).
> - **[MemoryService.swift](../../AgentChat/AgentChat/Services/MemoryService.swift)** — `updateGlobalProfile()`: авто-извлечение долговременной памяти (строгий промпт, без дублей); `extractTaskContext()`: авто-извлечение рабочей памяти.
> - **[ChatViewModel.swift](../../AgentChat/AgentChat/ViewModels/ChatViewModel.swift)** — `extractFactsOnLeave()`: обновление глобального профиля при уходе из чата; `updateTaskContext()`: авто-обновление рабочей памяти после каждого ответа; `saveToProfile()`: long-press → долговременная память.
> - **[ChatSession.swift](../../AgentChat/AgentChat/Models/ChatSession.swift)** — поле `taskContext: String?` (рабочая память, per-chat, SQLite).
> - **[MemorySheet.swift](../../AgentChat/AgentChat/Views/MemorySheet.swift)** — единый UI трёх слоёв памяти (кнопка 🧠 в тулбаре).
> - **[GlobalProfileSheet.swift](../../AgentChat/AgentChat/Views/GlobalProfileSheet.swift)** — редактор долговременной памяти (глобальный профиль).

> ▶ **Видео:** https://www.loom.com/share/448df13307fd48d991a8dd3fd7d1da4a

Продолжение приложения [AgentChat](../../AgentChat/). Развивает память дней 7–10: добавляет явную модель из трёх слоёв с раздельным хранением.

## Задача

Описать и реализовать модель памяти для ассистента. Разделить информацию минимум на 3 типа:
- **краткосрочная** — текущий диалог
- **рабочая** — данные текущей задачи
- **долговременная** — профиль, решения, знания

Сделать так, чтобы разные типы памяти хранились отдельно и явно выбиралось, что и куда сохраняется. Проверить влияние на ответы ассистента.

## Что сделано

### 3 слоя памяти

| Слой | Где хранится | Scope | Как наполняется |
|------|-------------|-------|-----------------|
| **Краткосрочная** | `ChatSession.messages` + `chat.summary` (SwiftData/SQLite) | per-chat | авто: окно N сообщений + сжатие старого в summary |
| **Рабочая** | `ChatSession.taskContext: String?` (SwiftData/SQLite) | per-chat | авто: LLM извлекает цели/решения/контекст задачи после каждого ответа |
| **Долговременная** | `UserDefaults("globalProfile")` | глобально — все чаты и агенты | авто при уходе из чата + вручную (редактор + long-press на сообщение) |

### Как собирается системный промпт

```
[SYSTEM BASE]          ← личность агента
[ДОЛГОВРЕМЕННАЯ]       ← globalProfile (UserDefaults) — если не пустой
[РАБОЧАЯ ПАМЯТЬ]       ← chat.taskContext (SQLite) — если не nil
[КРАТКОСРОЧНАЯ summary]← chat.summary (SQLite) — если есть
--- messages[N] ---    ← последние N сообщений окна
```

### Явный выбор что куда

- **Long-press на сообщение → «В долговременную память»** — текст мгновенно добавляется в глобальный профиль
- **Редактор профиля** (из 🧠 или настроек агента) — свободный текст, пользователь сам пишет
- **Авто-извлечение рабочей памяти** — LLM анализирует диалог после каждого ответа, извлекает контекст задачи
- **Авто-извлечение долговременной** — при уходе из чата, строгий промпт: только личная инфа о пользователе, без дублей, максимум 20 строк

### UI — кнопка 🧠

Открывает `MemorySheet` с тремя секциями:
- **Краткосрочная** — кол-во сообщений в окне + текст summary (если есть)
- **Рабочая** — извлечённый контекст задачи (или спиннер пока обновляется)
- **Долговременная** — глобальный профиль + кнопка «Редактировать»

## Значимый код (для проверяющих)

- [`Agent.swift`](../../AgentChat/AgentChat/Agent/Agent.swift) — `composedSystem()`: все 3 слоя инжектируются в system prompt.
- [`MemoryService.swift`](../../AgentChat/AgentChat/Services/MemoryService.swift) — `updateGlobalProfile()`: строгий промпт без дублей; `extractTaskContext()`: рабочая память.
- [`ChatSession.swift`](../../AgentChat/AgentChat/Models/ChatSession.swift) — поле `taskContext: String?`.
- [`ChatViewModel.swift`](../../AgentChat/AgentChat/ViewModels/ChatViewModel.swift) — `extractFactsOnLeave()`, `updateTaskContext()`, `saveToProfile()`, `globalProfile` (UserDefaults).
- [`MemorySheet.swift`](../../AgentChat/AgentChat/Views/MemorySheet.swift) — UI трёх слоёв (новый файл).
- [`GlobalProfileSheet.swift`](../../AgentChat/AgentChat/Views/GlobalProfileSheet.swift) — редактор профиля (новый файл).
- [`ChatView.swift`](../../AgentChat/AgentChat/Views/ChatView.swift) — кнопка 🧠 в toolbar, contextMenu «В долговременную память».
