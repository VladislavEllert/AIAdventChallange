<!-- source: memory-bank/web-app-status.md | title: web-app-status.md -->

# agent-web — Статус и архитектура

Дата: 2026-06-24. Полный web app портирован с agent-cli.

## Что сделано

| Компонент | Статус | Заметки |
|-----------|--------|---------|
| **Backend: FastAPI** | ✅ | SSE стриминг, DI, 25 тестов |
| **Frontend: React+Vite** | ✅ | TypeScript, Zustand, liquid glass |
| **Chat стриминг** | ✅ | `/api/chat/stream` → SSE (chunk, usage, violation, done) |
| **Invariant check** | ✅ | check_code() + check_llm() после ответа, rollback на нарушение |
| **Инвариант инжекция** | ✅ | `agent.invariants` → system prompt |
| **Profile инжекция** | ✅ | выбор профиля в UI → `profile_content` → system prompt |
| **Model switching** | ✅ | `/model` слеш-команда + UI кнопка → в запрос → agent.model |
| **3-layer memory** | ✅ | short_term (N сообщ), summary, working — видны в 🧠 панели |
| **N настройка** | ✅ | ⚙️ в MemoryPanel → settings.json → monkey-patch SUMMARIZE_AT/KEEP_RECENT |
| **Task FSM** | ✅ | ⚙️ панель, 4 этапа, live SSE output, confirm/feedback/pause |
| **Custom agents** | ✅ | Создание, удаление, вид в sidebar |
| **Sessions CRUD** | ✅ | Create, switch, delete (с confirmation modal) |
| **Profiles CRUD** | ✅ | View/edit markdown, extract facts из чата, toggle active |
| **Slash commands** | ✅ | /model, /new, /clear, /memory, /invariants, /profile, /task, /help |
| **Delete confirm** | ✅ | Modal при удалении агента или сессии |
| **Image attach** | ✅ | Upload → base64 → отправка в запрос |
| **Dark/Light theme** | ✅ | Toggle + system detection |
| **Button UX** | ✅ | Edit/delete buttons всегда видны (26×26px), красные при удалении |
| **Инвариант display** | ✅ | Список в 🛡️ панели, add/remove, violation alert |

## Критические гэпы, фиксированные сегодня

1. **Инварианты не проверялись** → добавил `check_code()` + `check_llm()` в chat router
2. **Инварианты не инжектировались** → добавил load + injection в `get_or_create()`
3. **Профиль не инжектировался** → добавил load + injection в chat router
4. **Модель из UI не передавалась** → добавил `activeModel` в ChatRequest

## Архитектура

```
Frontend (React)
  useAppStore: activeSessionId, activeModel, activeProfileName, activeAgentId
  streamChat(model, profile_name) → /api/chat/stream
  TaskPanel → /api/tasks/*
  MemoryPanel (⚙️ настройка N) → /api/settings
  InvariantsPanel → /api/invariants
  ProfilesPanel (toggle active) → /api/profiles
  
Backend (FastAPI)
  GET/PUT /api/settings (N, model)
  POST /api/chat/stream → 
    load invariants fresh
    load profile content (if profile_name)
    create/update agent with model + profile + invariants
    respond_stream_with_stats()
    check_code() + check_llm()
    if violation: pop_last_exchange(), rollback stats, emit 'violation' event
    else: emit 'usage' + 'done'
    
  /api/tasks/* → TaskRunner (thread + asyncio.Queue bridge)
  /api/invariants/* → load/add/delete from agent_cli store
  /api/profiles/* → read .md files from data/profiles/
  /api/memory/{id} → 3 layers + N from settings
  /api/agents/* → custom agents CRUD
  /api/sessions/* → named sessions CRUD
```

## Как тестировать

1. **Инварианты:**
   - Добавь инвариант "запрет на Python"
   - Ответь про Python
   - Должна быть красная alert + rollback сообщения

2. **Профиль:**
   - Выбери профиль в 👤 панели
   - Видишь зелёный "✓ Активен" + имя в StatusBar
   - Чат использует этот профиль

3. **Модель:**
   - `/model gpt-4o` → переключится
   - StatusBar покажет новую модель

4. **Task FSM:**
   - Нажми ⚙️ → Task tab
   - Введи задачу, запусти
   - Watch live 4-stage output

## Следующие сессии

- **Неделя 4:** MCP (инструменты, file read/write, exec)
- **Неделя 5:** RAG (документы, чанки, поиск)
- **Неделя 6:** VPS демо
- **Неделя 7:** Integration

Фундамент готов. Веб UI покрывает все эндпойнты, готов к расширению.

## Техдолг (опционально для недели 4+)

- Брейнсторм: multi-turn мультиагент без FSM (просто рой из N агентов)
- Сохранение потоков в сессиях (thread per message)
- Экспорт памяти как JSON (есть ручка, нет UI)
- Working memory UI (есть слой, не используется в чате)
- Caching (vector search на profile/invariants)
