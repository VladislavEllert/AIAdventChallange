"""Day 30 — parallel requests must not crash or cross-contaminate sessions."""
import threading

import agent_web.services.rate_limit as rl


def test_parallel_requests_stay_isolated_per_session(client):
    rl._hits.clear()

    session_ids = []
    for i in range(5):
        r = client.post("/api/sessions", json={"name": f"concurrent-{i}"})
        session_ids.append(r.json()["session_id"])

    results: dict[str, dict] = {}
    errors: list[Exception] = []

    def _run(sid: str):
        try:
            resp = client.post("/api/chat/stream", json={"session_id": sid, "message": f"hello from {sid}"})
            results[sid] = {"status": resp.status_code, "text": resp.text}
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_run, args=(sid,)) for sid in session_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"parallel requests raised: {errors}"
    assert len(results) == 5
    for sid, r in results.items():
        assert r["status"] == 200
        assert "event: done" in r["text"]

    # Each session's own history has exactly its own message — no cross-talk.
    for sid in session_ids:
        detail = client.get(f"/api/sessions/{sid}").json()
        user_messages = [m["content"] for m in detail["messages"] if m["role"] == "user"]
        assert user_messages == [f"hello from {sid}"]
