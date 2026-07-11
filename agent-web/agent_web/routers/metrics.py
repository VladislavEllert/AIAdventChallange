"""
Day 29 — proxies the Windows box's metrics_server so the frontend HUD doesn't
need to reach across the LAN directly (same-origin, and lets us cache/degrade).
"""
import time

import httpx
from fastapi import APIRouter

import agent_cli.config as cfg

router = APIRouter(tags=["metrics"])

_CACHE_TTL_S = 1.0
_cache: dict = {"data": None, "at": 0.0}


@router.get("/metrics")
def get_metrics():
    now = time.time()
    if _cache["data"] is not None and (now - _cache["at"]) < _CACHE_TTL_S:
        return _cache["data"]

    try:
        # Short timeout on purpose: an unreachable LAN host (Windows box off,
        # or metrics_server.py not running there) doesn't get an instant
        # "connection refused" like a closed localhost port would — the SYN
        # just goes unanswered until this timeout fires. 3s here made every
        # single poll (every 2s from the frontend) take a full 3s — bumped
        # this down so "offline" resolves fast instead of piling up requests.
        resp = httpx.get(cfg.METRICS_URL, timeout=0.8)
        resp.raise_for_status()
        data = resp.json()
        data["reachable"] = True
    except Exception:
        data = {"reachable": False}

    _cache["data"] = data
    _cache["at"] = now
    return data
