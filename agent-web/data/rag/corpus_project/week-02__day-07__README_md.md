<!-- source: week-02/day-07/README.md | title: README.md -->

# День 7 — Сохранение контекста (память агента)

> ⭐ **Главный код задания:**
> - **[MemoryService.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/Services/MemoryService.swift)** — сжатие диалога, извлечение фактов, JSON-экспорт (на дешёвой модели).
> - **[Agent.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/Agent/Agent.swift)** — `composedSystem()`: персона + долгие факты + summary.
> - **[ChatViewModel.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/ViewModels/ChatViewModel.swift)** — окно, сжатие, ручные/авто факты, восстановление при старте.

Приложение [AgentChat](../../AgentChat/) (продолжение дня-6).

## Задача

Агент сохраняет и восстанавливает контекст между запусками (JSON/SQLite),
продолжает диалог как будто не выключался.

## Что сделано

**Базовая персистенция (уже была в дне-6):** история чата хранится в **SQLite
через SwiftData** (`@Model StoredMessage`). При старте грузится назад
(`ChatViewModel.attach → open → loadHistory`). Закрыл приложение → открыл →
диалог на месте. Требование дня-7 закрыто.

**Апгрейд «по красоте» — слоистая память** (из конспекта недели 2):

```
system, который уходит в LLM =
    персона агента
  + долгие факты о юзере   (между чатами/сессиями)
  + summary старого        (сжатие)
  + последние N сообщений  (окно, не вся история)
```

1. **Долгая память (факты).** `AgentProfile.facts` — копилка фактов о
   пользователе, живёт между чатами агента, инжектится в system. Наполняется:
   - вручную: long-press по сообщению → «Запомнить»; правка списка в редакторе агента;
   - авто: при уходе из чата дешёвый вызов извлекает факты (`extractFacts`).
2. **Сжатие контекста.** В модель уходит окно последних `N=12` сообщений; старое
   сжимается в `ChatSession.summary` (роллинг, дешёвая модель). Экономит токены,
   не упирается в окно.
3. **JSON-экспорт.** Меню чата → «Экспорт памяти (JSON)»: показывает
   `{agent, facts, summary, messages}` — наглядно для видео.

**Стоимость:** все мета-вызовы (summary, авто-факты) — на самой дешёвой
`gemini/gemini-2.5-flash-lite`, и редко (summary только когда окно переросло,
факты — раз при уходе). Ручные факты — без LLM.

## Как проверить

1. **Персистенция:** напиши пару сообщений → закрой app полностью → открой →
   переписка на месте, продолжается.
2. **Долгая память (ручная):** «меня зовут Влад, люблю суши» → long-press →
   «Запомнить» → новый чат того же агента → «что я люблю?» → помнит.
3. **Долгая память (авто):** поговори → выйди из чата (на главную) → зайди в
   редактор агента → факты появились → в новом чате помнит.
4. **Сжатие:** длинный чат (>12 сообщений) → меню → JSON-экспорт → видно `summary`
   + окно последних сообщений (а не вся история).

## Архитектура памяти (3 механизма)

Не путать — это три РАЗНЫХ слоя:

**1. Окно последних N=12 — живой контекст ответа.**
Когда агент отвечает, в модель уходит `персона + самознание + факты + summary +
последние 12 сообщений`, а не вся история. Окно собирается в
`ChatViewModel.open()` (последние N из SQLite) и шлётся в `Agent.respond()`.

**2. Сжатие (summary) — старое за окном.**
Что выпадает за окно → дешёвый вызов сжимает в `ChatSession.summary` (роллинг,
копится). `ChatViewModel.compressIfNeeded()` → `MemoryService.summarize()`.
Экономит токены, держит суть длинного диалога.

**3. Долгая память (факты) — между чатами/сессиями.**
Отдельный «экстрактор» по ВСЕМУ диалогу при уходе из чата
(`ChatViewModel.extractFactsOnLeave()` → `MemoryService.extractFacts()`,
дешёвая модель), + ручное «Запомнить» (`ChatViewModel.remember()`, без LLM).
Факты дедупятся, лежат в `AgentProfile.facts` (SQLite) и инжектятся в `system`
КАЖДОГО чата агента (`Agent.composedSystem()`).

Плюс **самознание**: всем агентам в `system` добавлен блок про то, как устроена
их память (`Agent.selfKnowledge`) — агент честно объясняет себя, не врёт «всё
забываю в новом чате».

```
ты пишешь ──► [окно 12] + summary + facts ──► LLM ──► ответ
                   │
            выходишь из чата
                   ▼
        экстрактор (весь диалог) ──► новые факты ──► AgentProfile.facts (навсегда)
```

Все мета-вызовы (summary, извлечение фактов) — на `gemini/gemini-2.5-flash-lite`
и редко (cost-sensitive). Ручные факты — без LLM.

## Важные ссылки на код (для проверяющих)

- **[MemoryService.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/Services/MemoryService.swift)** — `summarize` (сжатие), `extractFacts` (извлечение фактов + дедуп), `exportJSON`.
- **[Agent.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/Agent/Agent.swift)** — `composedSystem()` (персона + самознание + факты + summary), `respond()`.
- **[ChatViewModel.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/ViewModels/ChatViewModel.swift)** — `open()` (окно+восстановление), `compressIfNeeded()`, `extractFactsOnLeave()`, `remember()`.
- **[ChatSession.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/Models/ChatSession.swift)** — SQLite-модели `ChatSession`(+`summary`)/`StoredMessage`.
- **[AgentProfile.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/Models/AgentProfile.swift)** — `facts` (долгая память на агента).

## Хранение: SQLite, не JSON-файл

Контекст лежит в SQLite (SwiftData, файл `default.store` в контейнере app), не в
коммитируемом JSON. JSON — только для наглядного экспорта. Это валидно по
условию («JSON **или** SQLite»).

## Видео

- [▶ Loom](https://www.loom.com/share/f35016674e984ab6a81f10998e507ba0)
