<!-- source: week-02/day-06/README.md | title: README.md -->

# День 6 — Первый агент (iOS)

> ⭐ **Главный код задания (логика вызова: агент → LLM):**
> - **[Agent.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/Agent/Agent.swift)** — агент-сущность, `respond()` собирает контекст (`system + история + user`) и зовёт транспорт. Логика инкапсулирована здесь.
> - **[ProxyAPIClient.swift](https://github.com/VladislavEllert/AIAdventChallange/blob/main/AgentChat/AgentChat/Networking/ProxyAPIClient.swift)** — сам HTTP-вызов LLM (URLSession → ProxyAPI), про агентов не знает.

Старт недели 2 (агенты). Реализован **агент как отдельная сущность**, а не голый
вызов API: логика запрос/ответ инкапсулирована внутри типа `Agent`. Интерфейс —
нативное iOS-приложение **AgentChat** (SwiftUI), которое ходит в LLM через ProxyAPI.

Это первый рабочий кусок (милстоун **M1**) большого приложения, спека которого
лежит в [`memory-bank/ios-agent-app/`](../../memory-bank/ios-agent-app/). Остальные
милстоуны (M2…M7) — по дням недели.

Код приложения: [`AgentChat/`](../../AgentChat/) (в корне репо — проект растёт всю неделю).

## Что сделано (M1 + сессионная память)

- Один агент-пресет **Бро 🤝** (неформальный собеседник) со своим system-промптом.
- Экран чата: лента сообщений, ввод, индикатор «печатает», баннер ошибок.
- Реальный вызов ProxyAPI (`POST /v1/chat/completions`), ответ на экране.
- **Сессионная память:** агент держит историю диалога и шлёт её в контекст —
  Бро помнит, что сказал выше в рамках запуска.
- Дизайн сразу нормальный: семантические цвета → тёмная тема из коробки,
  SF Symbols, скругления, автоскролл к низу. Переключатель темы в настройках.
- API-ключ хранится в **Keychain** (не в коде, не в бинаре, не в гите); вводится
  один раз в настройках.

## Агент как сущность (требование дня-6)

```
ChatView (SwiftUI)        тупой UI
  → ChatViewModel          состояние экрана, action send()
    → Agent                СУЩНОСТЬ: личность + история + respond()
      → ProxyAPIClient     тупой транспорт URLSession, про агентов не знает
```

Ключ инкапсуляции: UI зовёт `agent.respond(userInput)`, а **не** `client.post(...)`.
Внутри `Agent.respond(to:)` сам собирает `messages` (system + история + user),
зовёт транспорт, парсит, обновляет историю (коммит только при успехе).
Файл: [`AgentChat/AgentChat/Agent/Agent.swift`](../../AgentChat/AgentChat/Agent/Agent.swift).

## ProxyAPI

- base_url `https://openai.api.proxyapi.ru/v1`, `POST /chat/completions`.
- Auth: заголовок `Authorization: Bearer <PROXYAPI_KEY>`.
- Модель: `gemini/gemini-2.5-flash-lite` (префикс `gemini/` обязателен).
- Форма ответа сверена живым запросом: `choices[0].message.content`.

## Запуск

1. Открыть `AgentChat/AgentChat.xcodeproj` в Xcode (16+/26).
2. Выбрать таргет: iOS Simulator **или** свой iPhone (Signing → свой Apple ID,
   Automatic).
3. Run (⌘R). Первый запуск → настройки → вставить ключ ProxyAPI (уйдёт в Keychain).
4. Написать сообщение → Бро отвечает. Спросить уточнение со ссылкой на прошлое →
   проверить сессионную память.

> Для симулятора нужен загруженный iOS runtime
> (`xcodebuild -downloadPlatform iOS` или Xcode → Settings → Components).

## Статус

- Весь Swift-код типчекается под iOS (`swiftc -typecheck`, iPhoneSimulator SDK 26.5) — **OK**.
- Полная сборка/запуск — в Xcode пользователем (симулятор + реальный iPhone 13).

## Не входит (следующие дни недели)

M2 несколько агентов + SwiftData • M3 чаты внутри агента • M4 создание агентов •
M5 крутилки параметров • M6 модели+дизайн+темы • M7 долгая память между сессиями •
M8 бэкенд VPS (неделя 6).

## Ссылки

- Спека приложения: [`memory-bank/ios-agent-app/README.md`](../../memory-bank/ios-agent-app/README.md)
- Милстоуны: [`memory-bank/ios-agent-app/milestones.md`](../../memory-bank/ios-agent-app/milestones.md)
- Видео: [▶ Google Drive](https://drive.google.com/file/d/1oxYBNidlMzq5eve09l61oSuv6t2t1pWy/view?usp=sharing)
