from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS
from apscheduler.schedulers.background import BackgroundScheduler
import requests

mcp = FastMCP("AIAdvent Tools", host="0.0.0.0")

WATCHLIST = ["SBER", "GAZP", "YNDX", "LKOH"]
_moex_cache: dict[str, dict] = {}


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


def _update_moex_cache():
    for ticker in WATCHLIST:
        result = _fetch_moex(ticker)
        if result:
            _moex_cache[ticker] = result


scheduler = BackgroundScheduler()
scheduler.add_job(_update_moex_cache, "interval", seconds=30)
scheduler.start()
_update_moex_cache()


@mcp.tool()
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web for current information: news, prices, facts, recent events."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}\n{r['body']}\nURL: {r['href']}")
        return "\n\n".join(lines)
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


if __name__ == "__main__":
    import uvicorn
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
