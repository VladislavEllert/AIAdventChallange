<!-- source: week-04/day-18/README.md | title: README.md -->

# День 18 — 24/7 MCP: Background Data Collection

## 🎯 Цель
Собирать данные в фоне 24/7, хранить в SQLite, предоставлять историческую агрегацию через MCP.

## ⭐ Главный код задания

- **MCP сервер**: [`mcp-server/server.py`](../../mcp-server/server.py)
  - `_update_moex_cache()` (строки 109-122) — фоновая работа
  - `_save_snapshot()` (строки 40-55) — запись в БД с ротацией (MAX_RECORDS=10000)
  - `_init_db()` (строки 24-37) — SQLite таблица `snapshots`
  - `get_moex_history()` (строки 213-242) — агрегация за N минут

- **Scheduler**: APScheduler, `interval=30 сек` (строка 127)

- **Chat UI**: [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py)
  - Команда `/history TICKER [minutes]` (строки 112-122)
  - Стриминг результатов SSE

- **Frontend**: [`agent-web/frontend/src/components/chat/ChatInput.tsx`](../../agent-web/frontend/src/components/chat/ChatInput.tsx)
  - Autocomplete для `/history`: тикеры + периоды (30/60/120/480 мин)

## 📝 Что реализовано

1. **Фоновой сбор (APScheduler)**
   - Каждые 30 сек: `_update_moex_cache()` качает свежие цены
   - 8 акций + 2 индекса = 10 позиций
   - Каждое значение пишется в БД → 20 записей/мин → ~28800 в сутки

2. **SQLite ротация**
   - Таблица: `snapshots(id, ticker, value, ts)`
   - MAX_RECORDS=10000 на тикер
   - При переполнении: удаляются старые, остаются новые
   - 10000 записей ~8 часов истории

3. **Агрегация на лету**
   - `get_moex_history(ticker, minutes)` → SQL `WHERE ts >= datetime('now', '-N minutes')`
   - Возвращает: текущее, начальное, изменение %, min/max/avg

4. **Команда `/history`**
   - `/history IMOEX 60` → история IMOEX за последний час
   - Поддержка тикеров: IMOEX, RTSI, SBER, GAZP, YNDX, LKOH, MOEX, TCSG
   - Периоды: 30, 60, 120, 480 минут

## 🧪 Проверка

```bash
# 1. Запустить сервер (уже работает на VPS)
ssh root@194.226.115.120 'systemctl status mcp-server'

# 2. В чате: /history IMOEX 60
# → Должна вернуться агрегация за последний час

# 3. Посмотреть БД на VPS
# scp root@194.226.115.120:/opt/mcp-server-code/data/history.db ~/Desktop/
# TablePlus или sqlite3 ~/Desktop/history.db 'SELECT COUNT(*) FROM snapshots;'
```

## 📺 Видео
[День 18 — 24/7 Background Collection](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link)

## 📚 Знания
- **Background scheduling** — APScheduler, не блокирующий сбор
- **SQLite ротация** — DELETE ... WHERE id NOT IN (SELECT ... ORDER BY ts DESC LIMIT N)
- **Aggregation queries** — SQL на лету вместо хранения всех вычислений
- **VPS persistence** — systemd сервис перезапускается автоматически при падении
