import json
from unittest.mock import MagicMock, patch

from agent_web.services import comfyui_client


def test_build_prompt_fills_nodes():
    wf = comfyui_client.build_prompt("a cat", negative="blurry", seed=123, steps=15, cfg=7.5, width=512, height=768)
    assert wf["6"]["inputs"]["text"] == "a cat"
    assert wf["7"]["inputs"]["text"] == "blurry"
    assert wf["3"]["inputs"]["seed"] == 123
    assert wf["3"]["inputs"]["steps"] == 15
    assert wf["3"]["inputs"]["cfg"] == 7.5
    assert wf["5"]["inputs"]["width"] == 512
    assert wf["5"]["inputs"]["height"] == 768


def test_build_prompt_random_seed_when_none():
    wf1 = comfyui_client.build_prompt("x")
    wf2 = comfyui_client.build_prompt("x")
    # Not asserting inequality (could rarely collide) — just that it's a real int.
    assert isinstance(wf1["3"]["inputs"]["seed"], int)


def _mock_http_client(post_json, history_json, image_bytes=b"PNGDATA"):
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    post_resp = MagicMock()
    post_resp.json.return_value = post_json
    post_resp.raise_for_status = MagicMock()
    mock_client.post.return_value = post_resp

    hist_resp = MagicMock()
    hist_resp.json.return_value = history_json
    hist_resp.raise_for_status = MagicMock()

    img_resp = MagicMock()
    img_resp.content = image_bytes
    img_resp.raise_for_status = MagicMock()

    mock_client.get.side_effect = [hist_resp, img_resp]
    return mock_client


def test_generate_success_yields_progress_then_image():
    history = {
        "prompt-123": {
            "outputs": {
                "9": {"images": [{"filename": "out.png", "subfolder": "", "type": "output"}]}
            }
        }
    }
    mock_client = _mock_http_client({"prompt_id": "prompt-123"}, history)

    with patch("agent_web.services.comfyui_client.httpx.Client", return_value=mock_client):
        events = list(comfyui_client.generate("http://fake:8188", "a dog", poll_interval=0))

    types = [e["type"] for e in events]
    assert "progress" in types
    assert types[-1] == "image"
    assert events[-1]["data_b64"]


def test_generate_unreachable_yields_error():
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.side_effect = Exception("connection refused")

    with patch("agent_web.services.comfyui_client.httpx.Client", return_value=mock_client):
        events = list(comfyui_client.generate("http://fake:8188", "a dog"))

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "недоступен" in events[0]["message"]


def test_generate_timeout_yields_error():
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    post_resp = MagicMock()
    post_resp.json.return_value = {"prompt_id": "p1"}
    post_resp.raise_for_status = MagicMock()
    mock_client.post.return_value = post_resp

    hist_resp = MagicMock()
    hist_resp.json.return_value = {}  # never completes
    hist_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = hist_resp

    with patch("agent_web.services.comfyui_client.httpx.Client", return_value=mock_client):
        events = list(comfyui_client.generate("http://fake:8188", "a dog", poll_interval=0, timeout=0))

    assert events[-1]["type"] == "error"
    assert "Таймаут" in events[-1]["message"]
