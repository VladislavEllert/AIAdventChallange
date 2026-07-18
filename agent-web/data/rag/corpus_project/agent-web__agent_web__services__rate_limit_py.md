<!-- source: agent-web/agent_web/services/rate_limit.py | title: rate_limit.py -->

"""
Day 30 — simple in-memory rate limiter for the chat endpoint.

Home-LAN service, not internet-facing — this is a courtesy limiter against a
runaway client/script, not a security control. A sliding window per client IP,
no external dependency (slowapi would be overkill here).
"""
import time
from collections import defaultdict

from fastapi import HTTPException, Request

WINDOW_S = 60
MAX_REQUESTS = 30

_hits: dict[str, list[float]] = defaultdict(list)


def rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    hits = _hits[ip]
    hits[:] = [t for t in hits if now - t < WINDOW_S]
    if len(hits) >= MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Слишком много запросов — не больше {MAX_REQUESTS} за {WINDOW_S}с. Подожди немного.",
        )
    hits.append(now)
