# День 19 — MCP Composition: Auto Pipeline

## 🎯 Цель
Автоматическая цепочка из 3+ инструментов (получение → обработка → сохранение) без хардкода.

## ⭐ Главный код задания

- **MCP сервер (новые инструменты)**: [`mcp-server/server.py`](../../mcp-server/server.py)
  - `get_crypto_klines(symbol, interval, limit)` (строки 244-272) — Binance OHLCV
  - `calculate_indicators(klines_json)` (строки 275-318) — RSI/MACD/MA, сигнал buy/sell/hold
  - `save_report(filename, content)` (строки 321-333) — файл на VPS

- **Math helpers**: `_ema()`, `_calc_rsi()`, `_calc_macd()`, `_derive_signal()` (строки 178-240)

- **Chat handler**: [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py)
  - `/analyze SYMBOL [interval]` (строки 183-254)
  - **Гарантированная цепочка**: 4 шага выполняются ВСЕГДА (не может прерваться)

- **MCP client**: [`agent-web/agent_web/services/mcp_client.py`](../../agent-web/agent_web/services/mcp_client.py)
  - TOOL_LABELS для 3 новых тулов

## 📝 Что реализовано

1. **Крипто инструменты (Binance)**
   - `get_crypto_klines`: HTTPs запрос, парсинг JSON, возвращает OHLCV
   - Поддерживает: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT и любые пары
   - Интервалы: 15m, 1h, 4h, 1d

2. **Технический анализ (чистый Python)**
   - RSI(14) — классический Wilder smoothing
   - MACD(12,26,9) — EMA12 - EMA26, сигнальная линия EMA9
   - MA20, MA50 — простые средние
   - Автоматический сигнал: BUY 🟢 / SELL 🔴 / HOLD ⚪

3. **Гарантированный пайплайн**
   - Хардкодный `/analyze` обработчик (не полагаемся на LLM)
   - **Шаг 1**: `📊 Загружаю свечи...` → get_crypto_klines
   - **Шаг 2**: `🧮 Считаю RSI/MACD...` → calculate_indicators
   - **Шаг 3**: LLM генерирует анализ
   - **Шаг 4**: `💾 Сохраняю отчёт...` → save_report (ВСЕГДА, без пропусков)

4. **Сохранение артефактов**
   - Файлы: `/opt/reports/btcusdt_1h_analysis.md`, `ethusdt_4h_analysis.md`, и т.д.
   - Структура: # Заголовок + Индикаторы + Анализ LLM

## 🧪 Проверка

```bash
# 1. В чате написать (естественный язык):
# "Проанализируй биткоин за последние 50 часовых свечей"
# → Автоматически вызовутся все 4 шага

# 2. Посмотреть сохранённый отчёт
ssh root@194.226.115.120 'cat /opt/reports/btcusdt_1h_analysis.md'

# 3. Скачать отчёт себе
scp root@194.226.115.120:/opt/reports/btcusdt_1h_analysis.md ~/Desktop/
```

## 📺 Видео
[День 19 — MCP Composition & Auto Pipeline](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link)

## 📚 Знания
- **Tool composition** — LLM может не завершить цепочку (выберет "достаточно" результатов) → нужен хардкодный обработчик для гарантированности
- **EMA vs SMA** — EMA даёт больший вес свежим данным (лучше для реал-тайма)
- **RSI & MACD интерпретация** — RSI < 30 = перепродан, > 70 = перекуплен; MACD crossover = тренд
- **Artifact storage** — файлы — это память агента между сессиями (не теряется в контексте)
