import json
from unittest.mock import patch

import pytest


def _parse_sse(text: str) -> list[dict]:
    """Parse SSE response text into list of {event, data} dicts."""
    events = []
    event = ""
    for line in text.strip().split("\n"):
        if line.startswith("event: "):
            event = line[7:].strip()
        elif line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                events.append({"event": event, "data": data})
                event = ""
            except json.JSONDecodeError:
                pass
    return events


def test_chat_stream_requires_session(client):
    """Chat with non-existent session still creates agent (new session behavior)."""
    r = client.post("/api/chat/stream", json={
        "session_id": "new-session-xyz",
        "message": "hello"
    })
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]


def test_chat_stream_returns_chunks(client):
    r = client.post("/api/sessions", json={"name": "chat-test"})
    sid = r.json()["session_id"]

    r2 = client.post("/api/chat/stream", json={
        "session_id": sid,
        "message": "hello"
    })
    assert r2.status_code == 200

    events = _parse_sse(r2.text)
    event_types = [e["event"] for e in events]

    assert "chunk" in event_types
    assert "usage" in event_types
    assert "done" in event_types


def test_chat_stream_chunks_contain_text(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    r2 = client.post("/api/chat/stream", json={
        "session_id": sid,
        "message": "hi"
    })
    events = _parse_sse(r2.text)
    chunks = [e["data"]["text"] for e in events if e["event"] == "chunk"]
    full_text = "".join(chunks)
    assert len(full_text) > 0


def test_chat_stream_usage_has_fields(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    r2 = client.post("/api/chat/stream", json={
        "session_id": sid,
        "message": "test"
    })
    events = _parse_sse(r2.text)
    usage_events = [e for e in events if e["event"] == "usage"]
    assert len(usage_events) == 1

    usage = usage_events[0]["data"]
    assert "prompt_tokens" in usage
    assert "completion_tokens" in usage
    assert "cost_rub" in usage
    assert "elapsed_ms" in usage


def test_chat_saves_to_session(client):
    r = client.post("/api/sessions", json={"name": "persist-test"})
    sid = r.json()["session_id"]

    client.post("/api/chat/stream", json={"session_id": sid, "message": "remember this"})

    r2 = client.get(f"/api/sessions/{sid}")
    messages = r2.json()["messages"]
    assert len(messages) >= 2  # user + assistant
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "assistant" in roles


def test_chat_done_event_last(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    r2 = client.post("/api/chat/stream", json={"session_id": sid, "message": "go"})
    events = _parse_sse(r2.text)
    assert events[-1]["event"] == "done"


# ── day 27: image model (comfyui/sdxl) routes to a different SSE protocol ──

def _fake_comfy_events(*args, **kwargs):
    yield {"type": "progress", "pct": 50}
    yield {"type": "progress", "pct": 100}
    yield {"type": "image", "data_b64": "ZmFrZS1wbmc="}


def test_chat_stream_image_model_emits_image_events(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    with patch("agent_web.routers.chat.comfyui_client.generate", side_effect=_fake_comfy_events):
        r2 = client.post("/api/chat/stream", json={
            "session_id": sid,
            "message": "a red apple",
            "model": "comfyui/sdxl",
        })
    events = _parse_sse(r2.text)
    event_types = [e["event"] for e in events]

    assert "image_progress" in event_types
    assert "image" in event_types
    assert "chunk" not in event_types  # no token-streamed text for image model
    image_events = [e for e in events if e["event"] == "image"]
    assert image_events[0]["data"]["data_b64"] == "ZmFrZS1wbmc="


def test_chat_stream_image_model_error_falls_back_to_chunk(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    def _error_events(*args, **kwargs):
        yield {"type": "error", "message": "ComfyUI недоступен: connection refused"}

    with patch("agent_web.routers.chat.comfyui_client.generate", side_effect=_error_events):
        r2 = client.post("/api/chat/stream", json={
            "session_id": sid,
            "message": "a red apple",
            "model": "comfyui/sdxl",
        })
    events = _parse_sse(r2.text)
    chunk_texts = [e["data"]["text"] for e in events if e["event"] == "chunk"]
    assert any("ComfyUI" in t for t in chunk_texts)
    assert events[-1]["event"] == "done"
