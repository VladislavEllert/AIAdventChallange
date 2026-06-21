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
| 02 | 08 | Токены и контекстное окно: подсчёт токенов, рост ₽, стриминг, компактация в summary, что ломается при переполнении | done | [week-02/day-08](week-02/day-08/) · [AgentChat](AgentChat/) | [▶](https://www.loom.com/share/2f4052d188a34c45a730ead89fb72a7e) |
| 02 | 09 | Сжатие истории: последние N «как есть» + старое в summary, подстановка вместо полной истории, сравнение качества/токенов без и со сжатием | done | [week-02/day-09](week-02/day-09/) · [AgentChat](AgentChat/) | [▶](https://www.loom.com/share/cbeff47284d641ad913540f47d3b14e1) |
| 02 | 10 | Управление контекстом: 3 стратегии (без summary) — Sliding Window / Sticky Facts (KV) / Branching как 3 тест-агента + раздел «Мои \| Тестовые» | done | [week-02/day-10](week-02/day-10/) · [AgentChat](AgentChat/) | [▶](https://www.loom.com/share/2383219a98a4483cb535fb2230070678) |
| 03 | 11 | Модель памяти: 3 слоя (краткосрочная / рабочая / долговременная), авто-извлечение, MemorySheet UI | done | [week-03/day-11](week-03/day-11/) · [AgentChat](AgentChat/) | [▶](https://www.loom.com/share/448df13307fd48d991a8dd3fd7d1da4a) |
| 03 | 12 | Персонализация: слоистый профиль (стиль/правила/стек), 2 профиля → разные ответы, авто-роутинг фактов, CLI/TUI (Python) | done | [agent-cli](agent-cli/) | [▶](https://www.loom.com/share/46f41dfce33b4181bed14f6802d003f3) |
| 03 | 13 | Task State Machine: 4 стадии-агента (planning→execution→validation→done), детерминированные переходы, пауза / resume | done | [agent-cli](agent-cli/) | [▶](https://www.loom.com/share/e516f7eb3f634c52b6870968d3103ac2) |
| 03 | 14 | Инварианты: хранение отдельно от диалога, инжект в промпт, LLM-проверка, отказ при нарушении | done | [agent-cli](agent-cli/) | [▶](https://www.loom.com/share/216ee8cfa37f404087023ccd88672676) |
| 04 | 15 | Контролируемые переходы: рой 3 агентов на PLANNING + Оркестратор на каждой стадии, SQLite-сессии с персистом, `/session` switch/rename/delete, `/task jump` FSM-демо | done | [agent-cli](agent-cli/) | [▶](https://drive.google.com/file/d/17tSGsD85Gp4LIqengHKv3sk8l8zB9ZmK/view?usp=share_link) |

## Приложение AgentChat (неделя 2)

Нативное iOS-приложение (SwiftUI, iOS 17+): мульти-агентный чат поверх ProxyAPI.
Агент — отдельная сущность с личностью, памятью и инкапсулированной логикой вызова LLM.

Ключевой код:
- [`Agent.swift`](AgentChat/AgentChat/Agent/Agent.swift) — агент-сущность, `respond()` собирает контекст и зовёт транспорт.
- [`ProxyAPIClient.swift`](AgentChat/AgentChat/Networking/ProxyAPIClient.swift) — сам HTTP-вызов LLM (URLSession → ProxyAPI), про агентов не знает.

Спека и план: [`memory-bank/ios-agent-app/`](memory-bank/ios-agent-app/). Запуск — см. [`week-02/day-06/README.md`](week-02/day-06/README.md).
