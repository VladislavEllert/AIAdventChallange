"""Day 31: embedder backend selection + unknown backend rejection.

No live calls — ollama backend is exercised via urllib mock, proxyapi backend
is exercised via monkeypatching the OpenAI client construction path.
"""
from unittest.mock import MagicMock, patch

import pytest

from agent_web.services.rag import embedder


def test_unknown_backend_raises():
    with pytest.raises(ValueError, match="Unknown embed backend"):
        embedder.embed("hi", backend="not-a-backend")


def test_ollama_backend_calls_ollama_endpoint(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=30):
        captured["url"] = req.full_url
        import json as _json
        from io import BytesIO

        class Resp(BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        body = _json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode()
        return Resp(body)

    monkeypatch.setattr(embedder.urllib.request, "urlopen", fake_urlopen)
    vec = embedder.embed("hello", backend="ollama")
    assert "url" in captured
    assert "/api/embeddings" in captured["url"]
    assert len(vec) == 3


def test_proxyapi_backend_uses_openai_client(monkeypatch):
    fake_client = MagicMock()
    fake_client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.5] * 512)]
    )
    with patch("openai.OpenAI", return_value=fake_client) as mock_openai:
        vec = embedder.embed("hello", backend="proxyapi")

    mock_openai.assert_called_once()
    fake_client.embeddings.create.assert_called_once()
    call_kwargs = fake_client.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == embedder.EMBED_MODEL_PROXYAPI
    assert call_kwargs["dimensions"] == 512
    assert len(vec) == 512


def test_default_backend_is_ollama(monkeypatch):
    called = {}

    def fake_ollama(text):
        called["hit"] = True
        return [0.0]

    monkeypatch.setattr(embedder, "_embed_ollama", fake_ollama)
    embedder.embed("hi")
    assert called.get("hit") is True
