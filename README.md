# AI Advent Challenge #8 — рабочий журнал

Репозиторий прохождения курса **AI Advent Challenge #8** (Алексей Гладков, mobiledeveloper.tech).
7 недель практики по разработке с ИИ: код заданий, конспекты лекций, прогресс.

Подробности и правила: [`memory-bank/00-overview.md`](memory-bank/00-overview.md).
Конфиг для работы с Claude Code: [`CLAUDE.md`](CLAUDE.md).

## Структура

```
.
├── CLAUDE.md            # конфиг сессии, стиль общения, стек
├── memory-bank/         # постоянная память: правила, принципы, прогресс, конспекты
│   ├── 00-overview.md
│   ├── principles.md
│   ├── progress.md
│   ├── ios-agent-app/   # спека приложения AgentChat
│   └── lessons/
├── week-XX/day-YY/      # задания по дням (README + код/заметки)
└── AgentChat/           # iOS-приложение (неделя 2+): мульти-агентный чат на ProxyAPI
```

## Прогресс

| Неделя | День | Задача | Статус | Код | Видео |
|--------|------|--------|--------|-----|-------|
| 01 | 01 | Первый запрос к LLM через API (Telegram-бот на Gemini) | done | [week-01/day-01](week-01/day-01/) | [▶](https://www.loom.com/share/45330da8e4494e6ca49480a3420ff787) |
| 01 | 02 | Формат ответа: сравнение без/с ограничениями (формат, длина, stop) | done | [week-01/day-02](week-01/day-02/) | [▶](https://www.loom.com/share/866d3823571646c698e02f7b201d084b) |
| 01 | 03 | Разные способы рассуждения: 4 метода на задаче-ловушке «автомойка» | done | [week-01/day-03](week-01/day-03/) | [▶](https://www.loom.com/share/20f5f9c908834b5581588171f83c1cc2) |
| 01 | 04 | Температура: сравнение 0/0.7/1.2 (+top_p/top_k), точность ↔ креатив | done | [week-01/day-04](week-01/day-04/) | [▶](https://www.loom.com/share/70d345242d1446a8ada8343cbc50eb83) |
| 01 | 05 | Версии моделей: 1 промпт на 4 GPT, замер latency/токенов/₽ | done | [week-01/day-05](week-01/day-05/) | [▶](https://www.loom.com/share/80198dddfa8644c5b92ebf0823304d0c) |
| 02 | 06 | Первый агент: iOS-приложение **AgentChat** (мульти-агент, ProxyAPI) | done | [week-02/day-06](week-02/day-06/) · [AgentChat](AgentChat/) | [▶](https://drive.google.com/file/d/1oxYBNidlMzq5eve09l61oSuv6t2t1pWy/view?usp=sharing) |
| 02 | 07 | Сохранение контекста: SQLite-персистенция + долгая память (факты), сжатие, JSON-экспорт | done | [week-02/day-07](week-02/day-07/) · [AgentChat](AgentChat/) | [▶](https://www.loom.com/share/f35016674e984ab6a81f10998e507ba0) |

## Приложение AgentChat (неделя 2)

Нативное iOS-приложение (SwiftUI, iOS 17+): мульти-агентный чат поверх ProxyAPI.
Агент — отдельная сущность с личностью, памятью и инкапсулированной логикой вызова LLM.

Ключевой код:
- [`Agent.swift`](AgentChat/AgentChat/Agent/Agent.swift) — агент-сущность, `respond()` собирает контекст и зовёт транспорт.
- [`ProxyAPIClient.swift`](AgentChat/AgentChat/Networking/ProxyAPIClient.swift) — сам HTTP-вызов LLM (URLSession → ProxyAPI), про агентов не знает.

Спека и план: [`memory-bank/ios-agent-app/`](memory-bank/ios-agent-app/). Запуск — см. [`week-02/day-06/README.md`](week-02/day-06/README.md).
