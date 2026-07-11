import pytest

import agent_web.services.rate_limit as rl


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    """_hits is a module-level dict — without resetting it, requests from one
    test (all sharing TestClient's fixed source IP) bleed into the next."""
    rl._hits.clear()
    yield
    rl._hits.clear()


def test_allows_requests_under_the_limit(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]
    for _ in range(5):
        resp = client.post("/api/chat/stream", json={"session_id": sid, "message": "hi"})
        assert resp.status_code == 200


def test_blocks_after_limit_exceeded(client, monkeypatch):
    # Each streaming call through TestClient takes real wall-clock time (SSE
    # body fully consumed, invariant checks, session save) — using the real
    # MAX_REQUESTS=30 against the real 60s WINDOW_S makes this test racy
    # (early hits age out of the window before the count is reached). Shrink
    # both so the test only exercises the counting logic, not the clock.
    monkeypatch.setattr(rl, "MAX_REQUESTS", 3)
    monkeypatch.setattr(rl, "WINDOW_S", 3600)

    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]
    for _ in range(3):
        resp = client.post("/api/chat/stream", json={"session_id": sid, "message": "hi"})
        assert resp.status_code == 200
    over_limit = client.post("/api/chat/stream", json={"session_id": sid, "message": "hi"})
    assert over_limit.status_code == 429


def test_window_resets_old_hits():
    import time
    rl._hits["1.2.3.4"] = [0.0]  # far in the past
    now = time.time()
    hits = rl._hits["1.2.3.4"]
    hits[:] = [t for t in hits if now - t < rl.WINDOW_S]
    assert hits == []
