# День 11 — Модель памяти ассистента

## ⭐ Главный код задания

- [`Agent.swift`](../../AgentChat/AgentChat/Agent/Agent.swift) — `composedSystem()`: сборка промпта из 3 слоёв памяти
- [`MemoryService.swift`](../../AgentChat/AgentChat/Services/MemoryService.swift) — `updateGlobalProfile()`, `extractTaskContext()`: авто-извлечение в каждый слой
- [`ChatViewModel.swift`](../../AgentChat/AgentChat/ViewModels/ChatViewModel.swift) — `extractFactsOnLeave()`, `updateTaskContext()`, `saveToProfile()`
- [`MemorySheet.swift`](../../AgentChat/AgentChat/Views/MemorySheet.swift) — UI всех трёх слоёв (кнопка 🧠)

Видео: [▶ Яндекс.Диск](https://disk.yandex.ru/i/PB0YJYNtyL0-gA)

---

## Задание

🔥 День 11. Модель памяти ассистента

Описать и реализовать модель памяти для ассистента.

Разделить информацию минимум на 3 типа:
- краткосрочная (текущий диалог)
- рабочая (данные текущей задачи)
- долговременная (профиль, решения, знания)

Сделать так, чтобы:
- разные типы памяти хранились отдельно
- явно выбиралось, что и куда сохраняется

Проверить:
- какие данные попадают в каждый слой
- как это влияет на ответы ассистента

---

## Реализация

### 3 слоя памяти

| Слой | Хранение | Scope | Как наполняется |
|------|---------|-------|-----------------|
| Краткосрочная | `ChatSession.messages` + `chat.summary` (SwiftData/SQLite) | per-chat | автоматически — окно N сообщений + сжатие в summary |
| Рабочая | `ChatSession.taskContext: String?` (SwiftData/SQLite) | per-chat | авто-извлечение LLM после каждого ответа агента |
| Долговременная | `UserDefaults("globalProfile")` (plist) | глобально — все чаты и агенты | вручную (редактор + long-press) + авто при уходе из чата |

### Как собирается системный промпт (Agent.composedSystem)

```
[SYSTEM BASE]
<личность агента>

[ДОЛГОВРЕМЕННАЯ ПАМЯТЬ — глобальный профиль]
<UserDefaults globalProfile>          ← если не пустой

[РАБОЧАЯ ПАМЯТЬ — контекст задачи]
<ChatSession.taskContext>             ← если не nil

[КРАТКОСРОЧНАЯ — summary старого диалога]
<ChatSession.summary>                 ← если есть

--- messages[]: последние N сообщений ---
```

### UI — кнопка 🧠

Нажатие на 🧠 в тулбаре чата открывает `MemorySheet` с тремя секциями:
- **Краткосрочная** — кол-во сообщений в окне + текст summary
- **Рабочая** — извлечённый контекст задачи (или спиннер пока обновляется)
- **Долговременная** — глобальный профиль + кнопка редактировать

### Явный выбор что куда

- **Long-press на сообщение → «В долговременную память»** — текст сообщения мгновенно добавляется в globalProfile
- **Редактор профиля** — открывается из 🧠 или из настроек агента, свободный текст
- **Авто-извлечение рабочей памяти** — LLM анализирует диалог после каждого ответа, извлекает цель/решения/контекст задачи
- **Авто-извлечение долговременной** — при уходе из чата, строгий промпт: только личная инфа о пользователе, без дублей

### Ключевые файлы

```
AgentChat/AgentChat/
├── Agent/Agent.swift               — composedSystem(): сборка промпта
├── Services/MemoryService.swift    — updateGlobalProfile(), extractTaskContext()
├── Models/ChatSession.swift        — поле taskContext: String?
├── ViewModels/ChatViewModel.swift  — вся логика обновления слоёв
├── Views/MemorySheet.swift         — UI 3 слоёв (NEW)
├── Views/GlobalProfileSheet.swift  — редактор долговременной памяти (NEW)
└── Views/ChatView.swift            — кнопка 🧠, long-press contextMenu
```
