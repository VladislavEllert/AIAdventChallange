<!-- source: mcp-server/server.py | title: server.py -->

from mcp.server.fastmcp import FastMCP
from apscheduler.schedulers.background import BackgroundScheduler
from tavily import TavilyClient
import os
import sqlite3
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

_tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

mcp = FastMCP("AIAdvent Tools", host="0.0.0.0")

# ── Watchlists ────────────────────────────────────────────────────────────────
WATCHLIST = ["SBER", "GAZP", "YNDX", "LKOH", "MOEX", "TCSG", "ROSN", "NVTK"]
INDEX_WATCHLIST = ["IMOEX", "RTSI"]
_moex_cache: dict[str, dict] = {}
_index_cache: dict[str, dict] = {}

# ── SQLite (max 350 records per ticker) ──────────────────────────────────────
DB_PATH = os.getenv("MCP_DB_PATH", "/opt/mcp-server-code/data/history.db")
MAX_RECORDS = 10000


def _init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            value  REAL,
            ts     TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ticker_ts ON snapshots(ticker, ts)")
    conn.commit()
    conn.close()


def _save_snapshot(ticker: str, value: float):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO snapshots (ticker, value) VALUES (?, ?)", (ticker, value))
    # Keep only last MAX_RECORDS per ticker
    conn.execute("""
        DELETE FROM snapshots
        WHERE ticker = ?
          AND id NOT IN (
              SELECT id FROM snapshots
              WHERE ticker = ?
              ORDER BY ts DESC
              LIMIT ?
          )
    """, (ticker, ticker, MAX_RECORDS))
    conn.commit()
    conn.close()


# ── MOEX stock fetch ──────────────────────────────────────────────────────────
def _fetch_moex(ticker: str) -> dict | None:
    url = (
        f"https://iss.moex.com/iss/engines/stock/markets/shares"
        f"/boards/TQBR/securities/{ticker}.json"
    )
    try:
        r = requests.get(url, timeout=8)
        data = r.json()
        md = data.get("marketdata", {})
        cols = md.get("columns", [])
        rows = md.get("data", [])
        if not rows:
            return None
        row = dict(zip(cols, rows[0]))
        return {
            "ticker": ticker,
            "last": row.get("LAST"),
            "open": row.get("OPEN"),
            "volume": row.get("VOLRUR"),
        }
    except Exception:
        return None


# ── MOEX index fetch ──────────────────────────────────────────────────────────
def _fetch_moex_index(ticker: str) -> dict | None:
    url = (
        f"https://iss.moex.com/iss/engines/stock/markets/index"
        f"/boards/SNDX/securities/{ticker}.json"
    )
    try:
        r = requests.get(url, timeout=8)
        data = r.json()
        md = data.get("marketdata", {})
        cols = md.get("columns", [])
        rows = md.get("data", [])
        if not rows:
            return None
        row = dict(zip(cols, rows[0]))
        return {
            "ticker": ticker,
            "current": row.get("CURRENTVALUE"),
            "last": row.get("LASTVALUE"),
            "open": row.get("OPENVALUE"),
        }
    except Exception:
        return None


# ── APScheduler: refresh cache + write to SQLite ─────────────────────────────
def _update_moex_cache():
    for ticker in WATCHLIST:
        result = _fetch_moex(ticker)
        if result:
            _moex_cache[ticker] = result
            if result.get("last") is not None:
                _save_snapshot(ticker, result["last"])
    for ticker in INDEX_WATCHLIST:
        result = _fetch_moex_index(ticker)
        if result:
            _index_cache[ticker] = result
            val = result.get("current") or result.get("last")
            if val is not None:
                _save_snapshot(ticker, val)


_init_db()
scheduler = BackgroundScheduler()
scheduler.add_job(_update_moex_cache, "interval", seconds=30)
scheduler.start()
_update_moex_cache()


# ── Tools ─────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_current_datetime() -> str:
    """Get the current date and time. Always use this tool when the user asks what day/date/time it is."""
    MSK = timezone(timedelta(hours=3))
    now_msk = datetime.now(MSK)
    days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    months_ru = ["января", "февраля", "марта", "апреля", "мая", "июня",
                 "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    return (
        f"{days_ru[now_msk.weekday()]}, {now_msk.day} {months_ru[now_msk.month - 1]} {now_msk.year} года.\n"
        f"Время по Москве (UTC+3): {now_msk.strftime('%H:%M')}.\n"
        f"UTC: {datetime.now(timezone.utc).strftime('%H:%M')}.\n"
        f"Омск UTC+6: {datetime.now(timezone(timedelta(hours=6))).strftime('%H:%M')}."
    )


@mcp.tool()
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web for current information: news, product releases, prices, recent events, facts you are not sure about. Use this whenever the user asks about something that may have changed since your training cutoff (August 2025). Do NOT use for current date/time — use get_current_datetime instead."""
    try:
        resp = _tavily.search(
            query=query,
            max_results=num_results,
            include_answer=True,
            search_depth="advanced",
        )
        lines = []
        if resp.get("answer"):
            lines.append(f"Краткий ответ: {resp['answer']}\n")
        for i, r in enumerate(resp.get("results", []), 1):
            lines.append(f"{i}. {r['title']}\n{r['content']}\nURL: {r['url']}")
        return "\n\n".join(lines) if lines else "No results found."
    except Exception as e:
        return f"Search error: {e}"


@mcp.tool()
def get_moex_quote(ticker: str) -> str:
    """Get current stock price from Moscow Exchange (MOEX). Ticker examples: SBER, GAZP, YNDX."""
    ticker = ticker.upper()
    if ticker in _moex_cache:
        d = _moex_cache[ticker]
        return f"{ticker}: last={d['last']} RUB, open={d['open']}, volume={d['volume']}"
    result = _fetch_moex(ticker)
    if not result:
        return f"No data for {ticker}. Check ticker spelling."
    return f"{ticker}: last={result['last']} RUB, open={result['open']}, volume={result['volume']}"


@mcp.tool()
def get_moex_summary() -> str:
    """Get aggregated summary of tracked Moscow Exchange stocks (auto-updated every 30 sec)."""
    if not _moex_cache:
        return "Cache empty, try again in 30 seconds."
    lines = ["MOEX Watchlist (auto-refresh every 30s):"]
    for ticker, d in _moex_cache.items():
        lines.append(f"  {ticker}: {d['last']} RUB (open {d['open']})")
    return "\n".join(lines)


@mcp.tool()
def get_moex_index(ticker: str = "IMOEX") -> str:
    """Get current value of Moscow Exchange index in points. Use IMOEX (broad market, ~40 stocks) or RTSI (USD-denominated). Returns value, open, and % change."""
    ticker = ticker.upper()
    if ticker in _index_cache:
        d = _index_cache[ticker]
    else:
        d = _fetch_moex_index(ticker)
        if not d:
            return f"No data for index {ticker}. Valid tickers: IMOEX, RTSI."
    curr = d.get("current") or d.get("last")
    open_val = d.get("open")
    if curr and open_val:
        change = ((curr - open_val) / open_val) * 100
        sign = "▲" if change >= 0 else "▼"
        return f"{ticker}: {curr:.2f} пунктов {sign} {change:+.2f}% (открытие: {open_val:.2f})"
    return f"{ticker}: {curr} пунктов"


@mcp.tool()
def get_moex_history(ticker: str, minutes: int = 30) -> str:
    """Get historical price data for a stock or index from last N minutes (SQLite, updates every 30s). Returns min/max/avg/change. ticker: SBER, IMOEX, RTSI etc."""
    ticker = ticker.upper()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT value, ts FROM snapshots
        WHERE ticker = ?
          AND ts >= datetime('now', ? || ' minutes')
        ORDER BY ts ASC
    """, (ticker, f"-{minutes}")).fetchall()
    conn.close()

    if not rows:
        return f"Нет истории для {ticker} за {minutes} мин. Данные накапливаются каждые 30 сек — подождите немного."

    values = [r[0] for r in rows if r[0] is not None]
    if not values:
        return f"Нет данных для {ticker}."

    first, last = values[0], values[-1]
    change = ((last - first) / first * 100) if first else 0
    sign = "▲" if change >= 0 else "▼"
    return (
        f"{ticker} за {minutes} мин ({len(values)} замеров):\n"
        f"  Текущее:   {last:.2f}\n"
        f"  Начало:    {first:.2f}\n"
        f"  Изменение: {sign} {change:+.2f}%\n"
        f"  Мин: {min(values):.2f}  Макс: {max(values):.2f}\n"
        f"  Среднее:   {sum(values)/len(values):.2f}"
    )


# ── Crypto: math helpers ──────────────────────────────────────────────────────

def _ema(prices: list[float], period: int) -> list[float]:
    """Exponential moving average."""
    k = 2.0 / (period + 1)
    result = []
    prev = prices[0]
    for p in prices:
        prev = p * k + prev * (1 - k)
        result.append(prev)
    return result


def _calc_rsi(closes: list[float], period: int = 14) -> float:
    """RSI(period) — classic Wilder smoothing."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _calc_macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line) — last values."""
    if len(closes) < slow + signal:
        return 0.0, 0.0
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_series = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_series = _ema(macd_series, signal)
    return round(macd_series[-1], 6), round(signal_series[-1], 6)


def _derive_signal(rsi: float, macd: float, sig: float, price: float, ma20) -> str:
    """Simple rule-based signal."""
    bullish = 0
    bearish = 0
    if rsi < 30:
        bullish += 2
    elif rsi > 70:
        bearish += 2
    if macd > sig:
        bullish += 1
    else:
        bearish += 1
    if ma20 and price > ma20:
        bullish += 1
    elif ma20 and price < ma20:
        bearish += 1
    if bullish > bearish:
        return "BUY 🟢"
    elif bearish > bullish:
        return "SELL 🔴"
    return "HOLD ⚪"


# ── Crypto tools ──────────────────────────────────────────────────────────────

@mcp.tool()
def get_crypto_klines(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 50) -> str:
    """Fetch OHLCV candlestick data from Binance for crypto analysis.
    symbol examples: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT.
    interval: 15m, 1h, 4h, 1d.
    limit: number of candles (max 500).
    Returns JSON array with ts/open/high/low/close/volume fields."""
    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol.upper()}&interval={interval}&limit={limit}"
    )
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, dict) and data.get("code"):
            return f"Binance error: {data.get('msg', data)}"
        candles = [
            {
                "ts": c[0],
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5]),
            }
            for c in data
        ]
        return json.dumps(candles)
    except Exception as e:
        return f"Error fetching klines: {e}"


@mcp.tool()
def calculate_indicators(klines_json: str) -> str:
    """Calculate technical indicators (RSI, MACD, MA) from klines data returned by get_crypto_klines.
    Input: JSON string from get_crypto_klines.
    Returns: RSI(14), MACD(12,26,9), MA20, MA50, price summary and trading signal (BUY/SELL/HOLD)."""
    try:
        candles = json.loads(klines_json)
    except Exception:
        return "Error: invalid JSON. Pass output of get_crypto_klines directly."

    if not candles or len(candles) < 2:
        return "Not enough data (need at least 2 candles)."

    closes = [c["close"] for c in candles]
    current = closes[-1]
    symbol_hint = f"Last price: {current:.4f}"

    ma20 = round(sum(closes[-20:]) / min(20, len(closes)), 4)
    ma50 = round(sum(closes[-50:]) / min(50, len(closes)), 4) if len(closes) >= 10 else None

    rsi = _calc_rsi(closes)
    macd_line, signal_line = _calc_macd(closes)
    histogram = round(macd_line - signal_line, 6)
    signal = _derive_signal(rsi, macd_line, signal_line, current, ma20)

    rsi_zone = "перепродан (<30)" if rsi < 30 else "перекуплен (>70)" if rsi > 70 else "нейтральная зона"

    lines = [
        f"── Технический анализ ({len(closes)} свечей) ──",
        f"{symbol_hint}",
        f"MA(20):  {ma20}",
    ]
    if ma50:
        lines.append(f"MA(50):  {ma50}")
    lines += [
        f"RSI(14): {rsi}  [{rsi_zone}]",
        f"MACD:    {macd_line}  Signal: {signal_line}  Histogram: {histogram}",
        f"",
        f"Сигнал:  {signal}",
    ]
    return "\n".join(lines)


@mcp.tool()
def save_report(filename: str, content: str) -> str:
    """Save a text report to /opt/reports/ on the server.
    filename: e.g. 'btc_analysis.md' or 'eth_report.txt'.
    content: full text of the report.
    Returns confirmation with file path and size."""
    try:
        reports_dir = Path("/opt/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        # Sanitize filename — allow only safe chars
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")
        if not safe_name:
            safe_name = "report.txt"
        path = reports_dir / safe_name
        path.write_text(content, encoding="utf-8")
        MSK = timezone(timedelta(hours=3))
        ts = datetime.now(MSK).strftime("%Y-%m-%d %H:%M:%S МСК")
        return f"✅ Отчёт сохранён: {path}\n   Размер: {len(content)} символов\n   Время: {ts}"
    except Exception as e:
        return f"Error saving report: {e}"


if __name__ == "__main__":
    import uvicorn
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
