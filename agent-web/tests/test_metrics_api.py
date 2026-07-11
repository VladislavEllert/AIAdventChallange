from unittest.mock import MagicMock, patch


def test_metrics_reachable(client):
    fake_resp = MagicMock()
    fake_resp.json.return_value = {
        "cpu_pct": 12.3, "ram_used_gb": 8.0, "ram_total_gb": 16.0,
        "gpu_pct": 40.0, "vram_used_gb": 5.0, "vram_total_gb": 8.0,
        "gpu_temp_c": 65.0, "ollama_models": [{"name": "qwen3:4b", "size_vram_gb": 2.5}],
    }
    fake_resp.raise_for_status = MagicMock()

    with patch("agent_web.routers.metrics.httpx.get", return_value=fake_resp):
        r = client.get("/api/metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["reachable"] is True
    assert body["cpu_pct"] == 12.3
    assert body["ollama_models"][0]["name"] == "qwen3:4b"


def test_metrics_unreachable_returns_graceful_null(client):
    with patch("agent_web.routers.metrics.httpx.get", side_effect=Exception("connection refused")):
        # bypass the cache from a prior test in the same session
        import agent_web.routers.metrics as m
        m._cache["data"] = None
        r = client.get("/api/metrics")
    assert r.status_code == 200
    assert r.json() == {"reachable": False}


def test_metrics_caches_within_ttl(client):
    call_count = {"n": 0}

    def _get(*a, **kw):
        call_count["n"] += 1
        resp = MagicMock()
        resp.json.return_value = {"cpu_pct": 1.0}
        resp.raise_for_status = MagicMock()
        return resp

    import agent_web.routers.metrics as m
    m._cache["data"] = None
    with patch("agent_web.routers.metrics.httpx.get", side_effect=_get):
        client.get("/api/metrics")
        client.get("/api/metrics")
    assert call_count["n"] == 1  # second call served from cache
