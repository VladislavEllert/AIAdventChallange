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
├── AgentChat/           # iOS-приложение (неделя 2+): мульти-агентный чат на ProxyAPI
├── agent-cli/           # CLI/TUI (неделя 3+): Python, stateful-агент + Task FSM + инварианты
├── agent-web/           # Веб-приложение (день 15+): FastAPI + React, портирует CLI
└── mcp-server/          # MCP-сервер (неделя 4): FastMCP на VPS, web_search + MOEX котировки
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
| 04 | 16 | MCP: FastMCP-сервер на VPS (194.226.115.120:8001), 3 инструмента, day16_connect.py → список tools | done | [mcp-server](mcp-server/) | [▶](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link) |
| 04 | 17 | MCP: agent-web интегрирует tools (tool_start/tool_done SSE), web_search + get_moex_quote → живые ответы | done | [agent-web](agent-web/) · [mcp-server](mcp-server/) | [▶](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link) |
| 04 | 18 | MCP: APScheduler кэш MOEX каждые 30 сек, get_moex_history SQLite, /history команда | done | [agent-web](agent-web/) · [mcp-server](mcp-server/) | [▶](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link) |
| 04 | 19 | MCP Composition: get_crypto_klines → calculate_indicators (RSI/MACD) → save_report — гарантированный пайплайн | done | [agent-web](agent-web/) · [mcp-server](mcp-server/) | [▶](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link) |
| 04 | 20 | MCP Orchestration: два сервера (VPS финансы 8001 + GitHub 8003), роутинг по реестру, цепочка 4 тула 2 сервера | done | [agent-web](agent-web/) · [mcp-server](mcp-server/) | [▶](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link) |
| 05 | 21 | RAG: индексация 24 страниц GitLab Handbook (93k слов) → 2 стратегии chunking (fixed/structural) + Ollama `nomic-embed-text` 768-dim + JSON индекс с метаданными | done | [agent-web/scripts/rag](agent-web/scripts/rag/) · [agent-web/services/rag](agent-web/agent_web/services/rag/) | todo |
| 05 | 22 | RAG запрос: тумблер RAG в UI, ретрив top-5 чанков → контекст в промпт → стрим; 10 контрольных вопросов, `results_day22.md` — без RAG галлюцинации / с RAG факты | done | [agent-web](agent-web/) · [rag_eval](agent-web/rag_eval/) | todo |
| 05 | 23 | RAG фильтрация: query rewrite (LLM, перевод на английский) → cosine threshold filter → `rag_meta` SSE → badge в UI (raw→kept→used + rewritten query); сравнение RAG без фильтра / с фильтром на 10 вопросах, `results_day23.md` | done | [agent-web](agent-web/) · [rag_eval](agent-web/rag_eval/) | todo |

## Приложение AgentChat (неделя 2)

Нативное iOS-приложение (SwiftUI, iOS 17+): мульти-агентный чат поверх ProxyAPI.
Агент — отдельная сущность с личностью, памятью и инкапсулированной логикой вызова LLM.

Ключевой код:
- [`Agent.swift`](AgentChat/AgentChat/Agent/Agent.swift) — агент-сущность, `respond()` собирает контекст и зовёт транспорт.
- [`ProxyAPIClient.swift`](AgentChat/AgentChat/Networking/ProxyAPIClient.swift) — сам HTTP-вызов LLM (URLSession → ProxyAPI), про агентов не знает.

Спека и план: [`memory-bank/ios-agent-app/`](memory-bank/ios-agent-app/). Запуск — см. [`week-02/day-06/README.md`](week-02/day-06/README.md).

## Приложение agent-cli (неделя 3)

CLI/TUI на Python (prompt_toolkit + rich): полнофункциональный stateful-агент.

**Чем отличается от iOS:**
- Пауза в Task FSM с возможностью resume после закрытия
- Профиль пользователя как Markdown-файлы с авто-роутингом фактов
- Инварианты (правила) как отдельный слой, проверяются после каждого ответа
- Рой 3 агентов на стадии PLANNING + Оркестратор на всех стадиях
- Именованные сессии в SQLite с полным персистом (state machine, модель, профиль)
- Все `/` команды: `/model`, `/profile`, `/invariants`, `/task`, `/session`, `/state`, `/help`

Ключевой код:
- [`core/agent.py`](agent-cli/agent_cli/core/agent.py) — Agent с `respond_stream_with_stats()`, auto-summarize на N сообщ.
- [`core/memory.py`](agent-cli/agent_cli/core/memory.py) — 3 слоя: short_term (последние N), summary (старое сжатое), working (рабочая память)
- [`core/prompt_builder.py`](agent-cli/agent_cli/core/prompt_builder.py) — система промптов: persona + profile + summary + invariants
- [`state/coordinator.py`](agent-cli/agent_cli/state/coordinator.py) — Task FSM: planning → execution → validation → done
- [`invariants/checker.py`](agent-cli/agent_cli/invariants/checker.py) — check_code() (fast) + check_llm() (thorough) с rollback при нарушении
- [`tui.py`](agent-cli/agent_cli/tui.py) — интерфейс, REPL, slash-команды

Старт: `python -m agent_cli`.

## Приложение agent-web (день 15+)

Веб-приложение (FastAPI + React, Vite): портирует все функции agent-cli с улучшенным UI.

**Архитектура:**
- **Backend:** FastAPI с SSE стримингом, Zustand для state management в памяти (no DB для агентов)
- **Frontend:** React, Vite, TypeScript; liquid glass дизайн с dark/light theme
- **Стриминг:** `/api/chat/stream` → SSE события (chunk, violation, usage, done)
- **Инварианты:** check_code() + check_llm() после каждого ответа, rollback при нарушении
- **Профили:** ProfilesPanel выбирает профиль → инжектируется в system prompt каждого запроса
- **Модель:** UI переключает модель → отправляется в chat request → агент использует её
- **Task FSM:** Отдельная панель ⚙️ → SSE stream стадий (planning, execution, validation, done) с live output
- **Память:** 3 слоя видны в 🧠 панели, N настраивается через ⚙️ в MemoryPanel

Ключевой код:
- [`agent_web/routers/chat.py`](agent-web/agent_web/routers/chat.py) — SSE stream + инвариант проверка + rollback
- [`agent_web/services/agent_manager.py`](agent-web/agent_web/services/agent_manager.py) — per-session Agent cache
- [`agent_web/services/task_runner.py`](agent-web/agent_web/services/task_runner.py) — TaskCoordinator в thread + asyncio.Queue → SSE
- [`frontend/src/api/chat.ts`](agent-web/frontend/src/api/chat.ts) — streamChat() с model + profile_name
- [`frontend/src/components/panels/MemoryPanel.tsx`](agent-web/frontend/src/components/panels/MemoryPanel.tsx) — 3 слоя памяти + N настройка
- [`frontend/src/components/panels/TaskPanel.tsx`](agent-web/frontend/src/components/panels/TaskPanel.tsx) — Task FSM UI с confirm/feedback
- [`frontend/src/stores/useAppStore.ts`](agent-web/frontend/src/stores/useAppStore.ts) — activeSessionId, activeModel, activeProfileName, rightPanelTab

**Запуск:**
```bash
cd agent-web
python -m agent_web  # FastAPI на localhost:8765
cd frontend && npm run dev  # React на localhost:5173
```
Браузер: `http://localhost:5173`
