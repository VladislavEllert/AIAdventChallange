# День 8 — Работа с токенами и контекстным окном

> ⭐ **Главный код задания:**
> - **[ProxyAPIClient.swift](../../AgentChat/AgentChat/Networking/ProxyAPIClient.swift)** — `completeStreaming()`: SSE-стриминг + парсинг `usage` (токены).
> - **[Agent.swift](../../AgentChat/AgentChat/Agent/Agent.swift)** — `respondStreaming()`: стрим дельт, точный usage, обрезка старого при переполнении.
> - **[ChatViewModel.swift](../../AgentChat/AgentChat/ViewModels/ChatViewModel.swift)** — `send()`, `compactNow()`/`compressIfNeeded()` (компактация), демо-лимит, агрегаты токенов/₽.
> - **[LLMModel.swift](../../AgentChat/AgentChat/Models/LLMModel.swift)** — `contextLimit` по провайдерам + `cost(usage)` в ₽.

> ▶ **Видео:** https://www.loom.com/share/2f4052d188a34c45a730ead89fb72a7e

Продолжение приложения [AgentChat](../../AgentChat/) (недели 2).

## Задача

Добавить подсчёт токенов (текущий запрос / вся история / ответ), показать рост стоимости
по ходу диалога и продемонстрировать, что ломается при переполнении контекста.

## Что сделано

- **Подсчёт токенов.** Точные числа из `usage` ответа API: вход (`prompt` = system + история +
  запрос), выход (`completion` = ответ), `total`, `reasoning`. Под каждым ответом —
  `↑вход ↓выход Σвсего ₽ время`. Под запросом — `≈` грубая локальная оценка до отправки.
- **Рост стоимости.** Вся история пере-отправляется каждый ход → вход и Σток/₽ растут.
  Видно в HUD-метре контекста и счётчике диалога.
- **Стриминг.** Ответ печатается токен-за-токеном (SSE, `stream_options.include_usage`).
- **Что ломается при переполнении.** Голая LLM при переполнении окна просто падает (400).
  Контекст урезает само приложение: окно + сжатие старого в `summary` (как авто-compact в
  Claude Code). Сжатие лоссовое и избирательное → детали теряются → модель забывает/галлюцинирует.
- **Демо-крутилки (учебные):** демо-лимит контекста, размер окна, степень сжатия — чтобы
  переполнение и забывание были видны на видео, не упираясь в реальный лимит модели (128k+).
- **Под капотом:** лист «Статистика чата» (токены, срез окна, текущая summary) и JSON-экспорт.

## Значимый код (для проверяющих)

- [`ProxyAPIClient.swift`](../../AgentChat/AgentChat/Networking/ProxyAPIClient.swift) — `completeStreaming()`: SSE-стриминг + парсинг `usage`.
- [`Agent.swift`](../../AgentChat/AgentChat/Agent/Agent.swift) — `respondStreaming()`: стрим дельт, точный usage, токен-бюджет (обрезка старого при переполнении).
- [`TokenUsage.swift`](../../AgentChat/AgentChat/Models/TokenUsage.swift) · [`TokenEstimator.swift`](../../AgentChat/AgentChat/Services/TokenEstimator.swift) — расход токенов и локальная оценка.
- [`LLMModel.swift`](../../AgentChat/AgentChat/Models/LLMModel.swift) — `contextLimit` по провайдерам + `cost(usage)` в ₽.
- [`ChatViewModel.swift`](../../AgentChat/AgentChat/ViewModels/ChatViewModel.swift) — `send()` (стрим), `compactNow()`/`compressIfNeeded()` (компактация в summary), демо-лимит, агрегаты.
- [`MemoryService.swift`](../../AgentChat/AgentChat/Services/MemoryService.swift) — `summarize()` (сжатие), `exportJSON()` (токены), фильтр извлечения фактов.
- UI: [`MessageBubble.swift`](../../AgentChat/AgentChat/Views/MessageBubble.swift) (мета токенов), [`ChatView.swift`](../../AgentChat/AgentChat/Views/ChatView.swift) (HUD-метр), [`ChatStatsSheet.swift`](../../AgentChat/AgentChat/Views/ChatStatsSheet.swift) (статистика + summary).

## Как проверить

1. Короткий диалог → под ответом токены/₽/время; ответ идёт стримингом.
2. Длинный диалог → вход (prompt) и Σток/₽ растут каждый ход.
3. Настройки → демо-лимит ~1000, сжатие «Жёсткая» → метр заполняется, появляются плашки
   «Контекст сжат … summary пересобран N→M слов».
4. Спросить про деталь из начала, что выпала из окна и не попала в summary → модель забыла/придумала.
   Контраст: демо-лимит ВЫКЛ → помнит. Это и есть поломка при переполнении.

## Вывод

Токены = деньги; история пере-шлётся каждый ход → стоимость растёт. Модель сама контекстом не
управляет — это делает приложение (окно + summary + долгая память фактами). Сжатие лоссовое →
теряются детали → отсюда галлюцинации. Правильное управление контекстом критично.
